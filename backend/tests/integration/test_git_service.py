"""
Tests for GitRepositoryService.
"""

import uuid
from pathlib import Path
from unittest import mock

import pytest

from app.modules.repositories.git_service import GitRepositoryService


@pytest.fixture
def git_service(tmp_path: Path, monkeypatch) -> GitRepositoryService:
    monkeypatch.setattr("app.core.config.settings.repository_workspace_root", str(tmp_path))
    repo_id = uuid.uuid4()
    ingest_id = uuid.uuid4()
    return GitRepositoryService(repository_id=repo_id, ingestion_id=ingest_id)


def test_prepare_and_cleanup_workspace(git_service: GitRepositoryService):
    """Test workspace directory management."""
    git_service.prepare_workspace()
    
    assert git_service.source_dir.exists()
    assert git_service.source_dir.is_dir()
    
    # Create a dummy file to test cleanup
    (git_service.source_dir / "test.txt").write_text("hello")
    
    git_service.cleanup_workspace()
    
    assert not git_service.ingestion_dir.exists()


@mock.patch("subprocess.run")
def test_clone_repository_success(mock_subprocess_run, git_service: GitRepositoryService):
    """Test cloning process uses proper credentials helper and safely executes."""
    # Mock subprocess.run responses for clone and rev-parse
    mock_clone_result = mock.Mock()
    mock_clone_result.returncode = 0
    
    mock_rev_result = mock.Mock()
    mock_rev_result.stdout = "abc123def456\n"
    
    def side_effect_subprocess(*args, **kwargs):
        # Create the .git dir when clone is called
        if args[0][1] == "clone":
            (git_service.source_dir / ".git").mkdir(parents=True, exist_ok=True)
            return mock_clone_result
        return mock_rev_result
        
    mock_subprocess_run.side_effect = side_effect_subprocess
    
    commit_sha = git_service.clone_repository(
        full_name="test/repo",
        default_branch="main",
        github_token="secret_token"
    )
        
    assert commit_sha == "abc123def456"
    assert mock_subprocess_run.call_count == 2
    
    # Verify the clone command args
    clone_call_args = mock_subprocess_run.call_args_list[0][0][0]
    assert clone_call_args[0] == "git"
    assert clone_call_args[1] == "clone"
    assert "https://github.com/test/repo.git" in clone_call_args
    
    # Verify that the token is NEVER passed in the git clone url directly
    # It should be using the credential helper
    assert not any("secret_token" in arg for arg in clone_call_args)
    
    # Verify the temporary credential file is cleaned up
    creds_file = git_service.ingestion_dir / ".git-credentials"
    assert not creds_file.exists()


@mock.patch("subprocess.run")
def test_clone_repository_failure(mock_subprocess_run, git_service: GitRepositoryService):
    """Test error handling when cloning fails."""
    mock_clone_result = mock.Mock()
    mock_clone_result.returncode = 128
    mock_clone_result.stderr = "Authentication failed"
    
    mock_subprocess_run.return_value = mock_clone_result
    
    with pytest.raises(RuntimeError, match="Failed to clone repository"):
        git_service.clone_repository(
            full_name="test/repo",
            default_branch="main",
            github_token="invalid_token"
        )
        
    # Verify credentials file is still cleaned up even on exception
    creds_file = git_service.ingestion_dir / ".git-credentials"
    assert not creds_file.exists()
