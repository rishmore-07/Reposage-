"""
app/modules/repositories/file_discovery.py

Recursively discovers and filters files in a cloned repository.
Calculates basic metadata and SHA-256 hashes without semantic parsing.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Common dependency/build directories to ignore
IGNORED_DIRECTORIES = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "dist",
    "build",
    "coverage",
    ".next",
    ".cache",
    "vendor",
    "target",
}

# Obvious sensitive files to avoid indexing
SENSITIVE_FILES_EXACT = {
    ".env",
    "credentials.json",
    "secrets.json",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
}

SENSITIVE_EXTENSIONS = {
    ".pem",
    ".key",
    ".crt",
    ".p12",
    ".pfx",
}

# Known binary extensions to speed up detection
BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg",
    ".pdf", ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar",
    ".mp4", ".mp3", ".wav", ".avi", ".mkv",
    ".exe", ".dll", ".so", ".dylib", ".bin",
    ".pyc", ".class", ".o", ".a", ".lib",
}


def is_binary_content(file_path: Path) -> bool:
    """
    Check if a file is binary by looking for null bytes in the first chunk.
    """
    try:
        with open(file_path, "rb") as f:
            chunk = f.read(1024)
            return b"\x00" in chunk
    except Exception:
        # If we can't read it, safely assume binary to prevent indexing errors
        return True


def calculate_sha256(file_path: Path) -> str:
    """
    Calculates the SHA-256 hash of a file using streaming reads.
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


class FileDiscoveryService:
    """
    Discovers files in an isolated workspace, adhering to limits and filtering rules.
    """

    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root.resolve()
        self.max_file_size = settings.max_file_size_bytes
        self.max_repo_size = settings.max_repository_size_bytes
        self.max_file_count = settings.max_file_count
        self.max_depth = settings.max_directory_depth

    def discover_files(self) -> list[dict]:
        """
        Recursively walks the workspace root and returns a list of dictionaries
        containing file metadata.
        
        Raises RuntimeError if repository size limits are exceeded.
        """
        discovered_files = []
        total_size = 0

        # We'll use os.walk which traverses recursively
        for root, dirs, files in os.walk(self.workspace_root, followlinks=False):
            current_path = Path(root).resolve()
            
            # Check directory depth
            try:
                rel_dir = current_path.relative_to(self.workspace_root)
            except ValueError:
                # Outside workspace root (shouldn't happen with os.walk but safety check)
                continue
                
            if len(rel_dir.parts) > self.max_depth:
                # Prune further traversal in this branch
                dirs.clear()
                continue

            # Filter out ignored directories so os.walk doesn't traverse them
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRECTORIES]

            for file_name in files:
                if len(discovered_files) >= self.max_file_count:
                    logger.warning("max_file_count_reached", count=self.max_file_count)
                    return discovered_files

                # Filter sensitive exact file names
                if file_name in SENSITIVE_FILES_EXACT or file_name.startswith(".env."):
                    continue

                file_path = current_path / file_name

                # Symlink security check
                if file_path.is_symlink():
                    try:
                        resolved_target = file_path.resolve(strict=True)
                        # Check if the resolved target is within the workspace root
                        if self.workspace_root not in resolved_target.parents and resolved_target != self.workspace_root:
                            logger.warning("symlink_escape_prevented", link=str(file_path))
                            continue
                    except Exception:
                        # Broken symlink or unable to resolve
                        continue
                        
                    # If it's a valid symlink inside workspace, update file_path to the real target
                    # Actually, if we follow symlinks we might process the same file twice.
                    # It's safer to just skip symlinks for initial file discovery to prevent loops
                    # unless explicitly requested, or just record them as they are.
                    # For safety, we will process the target but skip if it's a directory (handled by os.walk).
                    file_path = file_path.resolve()
                    if file_path.is_dir():
                        continue

                # Filter sensitive extensions
                ext = file_path.suffix.lower()
                if ext in SENSITIVE_EXTENSIONS:
                    continue

                try:
                    file_stat = file_path.stat()
                except OSError:
                    continue

                size = file_stat.st_size

                # Oversize file check
                if size > self.max_file_size:
                    logger.warning("file_too_large_skipped", file=file_name, size=size)
                    continue

                # Cumulative repository size check
                if total_size + size > self.max_repo_size:
                    raise RuntimeError(f"Repository exceeds maximum allowed size of {self.max_repo_size} bytes.")

                total_size += size

                # Binary detection
                is_binary = ext in BINARY_EXTENSIONS
                if not is_binary and size > 0:
                    is_binary = is_binary_content(file_path)

                # Hash calculation
                try:
                    file_hash = calculate_sha256(file_path)
                except Exception as e:
                    logger.error("file_hash_failed", file=file_name, error=str(e))
                    continue
                    
                rel_path = file_path.relative_to(self.workspace_root).as_posix()

                discovered_files.append({
                    "relative_path": rel_path,
                    "file_size": size,
                    "extension": ext,
                    "is_binary": is_binary,
                    "file_hash": file_hash,
                })

        return discovered_files
