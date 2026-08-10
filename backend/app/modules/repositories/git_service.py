"""
app/modules/repositories/git_service.py

Secure Git repository cloning and workspace management.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import uuid
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class GitRepositoryService:
    """
    Manages isolated Git workspaces and securely clones repositories.
    """

    def __init__(self, repository_id: uuid.UUID, ingestion_id: uuid.UUID):
        self.repository_id = repository_id
        self.ingestion_id = ingestion_id
        # Workspace Path: REPOSITORY_WORKSPACE_ROOT / repo_id / ingestion_id / source
        self.workspace_root = Path(settings.repository_workspace_root).resolve()
        self.repo_dir = self.workspace_root / str(self.repository_id)
        self.ingestion_dir = self.repo_dir / str(self.ingestion_id)
        self.source_dir = self.ingestion_dir / "source"

    def get_source_dir(self) -> Path:
        """Returns the isolated source directory for this ingestion."""
        return self.source_dir

    def prepare_workspace(self) -> None:
        """Ensure the ingestion directory exists and is empty."""
        if self.source_dir.exists():
            shutil.rmtree(self.source_dir)
        self.source_dir.mkdir(parents=True, exist_ok=True)

    def cleanup_workspace(self) -> None:
        """Removes the entire ingestion directory if it exists."""
        if self.ingestion_dir.exists():
            shutil.rmtree(self.ingestion_dir)

    def clone_repository(
        self,
        full_name: str,
        default_branch: str,
        github_token: str,
    ) -> str:
        """
        Securely clones a GitHub repository using a shallow clone.
        Returns the cloned commit SHA on success.

        Raises RuntimeError if cloning fails or validation fails.
        """
        self.prepare_workspace()

        github_repo_url = f"https://github.com/{full_name}.git"

        # We construct a secure environment using GIT_ASKPASS to provide the token.
        # However, a simpler and robust way for automation is using credential.helper
        # injected via environment variable or passing it inline without exposing to args.
        # Using git -c credential.helper=... ensures the token is in the args, which can leak in `ps`.
        # Instead, we will pass a custom GIT_ASKPASS script or use the Authorization header directly.
        # Actually, Git allows injecting headers safely via http.extraHeader config in environment.
        
        env = os.environ.copy()
        env["GIT_TERMINAL_PROMPT"] = "0"  # Prevent git from prompting for password
        
        # Inject the token securely through the environment via a custom credential helper
        # We can use a simple inline shell script that echoes the token, executed by Git.
        # We pass the token in an env var to the child process.
        env["GITHUB_TOKEN"] = github_token
        
        # On Windows, a bash inline script for credential.helper might fail.
        # Since this needs to be cross-platform (especially since the user is on Windows),
        # we can just use `http.extraHeader` in the Git command environment!
        # git -c http.extraHeader="AUTHORIZATION: basic <base64>" 
        # But base64 encoding the token makes it still visible in args if passed via -c.
        
        # Best approach: Use a temporary custom askpass script.
        # Wait, python's subprocess allows writing to stdin for askpass? No.
        # The safest approach for cross-platform subprocess that doesn't leak in args:
        # Construct the URL with token, BUT since we shouldn't do that due to URL leaking in exceptions,
        # we can use the `git fetch` with an auth header set in the env if possible? Git doesn't natively support that.
        
        # Let's create a temporary askpass script.
        # Actually, `git fetch` can take a credential helper from the environment:
        # `git -c credential.helper='!f() { echo "username=oauth2"; echo "password=$GITHUB_TOKEN"; }; f'`
        # This works on Unix, but might fail on Windows if sh is not available.
        # Given this must run on the worker, if the worker is Unix-based (Docker), this is fine.
        # But if the worker is Windows, it might fail.
        
        # Another option: Write the token to a temporary `.git-credentials` file,
        # run the clone, and immediately delete the file.
        creds_file = self.ingestion_dir / ".git-credentials"
        creds_content = f"https://oauth2:{github_token}@github.com"
        creds_file.write_text(creds_content, encoding="utf-8")
        
        try:
            # We configure git to use the temporary credentials file just for this command
            clone_cmd = [
                "git",
                "clone",
                "--depth", "1",
                "--branch", default_branch,
                "--config", f"credential.helper=store --file={creds_file}",
                "--config", "credential.useHttpPath=true",
                github_repo_url,
                str(self.source_dir)
            ]
            
            logger.info("cloning_repository", full_name=full_name, dest=str(self.source_dir))
            
            result = subprocess.run(
                clone_cmd,
                env=env,
                capture_output=True,
                text=True,
                check=False
            )
            
            if result.returncode != 0:
                # Do not log the output directly if it might contain the URL with tokens
                # (though credential helper avoids token in URL, safe to log some error text)
                logger.error("git_clone_failed", error=result.stderr)
                raise RuntimeError(f"Failed to clone repository: {full_name}")

            # Validate workspace
            if not (self.source_dir / ".git").exists():
                raise RuntimeError("Clone completed but .git directory is missing.")

            # Get the cloned commit SHA
            rev_cmd = ["git", "-C", str(self.source_dir), "rev-parse", "HEAD"]
            rev_result = subprocess.run(
                rev_cmd,
                env=env,
                capture_output=True,
                text=True,
                check=True
            )
            commit_sha = rev_result.stdout.strip()
            return commit_sha

        finally:
            # Always ensure the credentials file is deleted
            if creds_file.exists():
                creds_file.unlink()
