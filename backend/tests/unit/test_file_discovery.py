"""
Tests for FileDiscoveryService.
"""

import os
from pathlib import Path

import pytest
from app.modules.repositories.file_discovery import FileDiscoveryService


def test_file_discovery_basic(tmp_path: Path):
    """Test discovering normal files and filtering sensitive files."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    
    # Normal files
    (repo_root / "main.py").write_text("print('hello')", encoding="utf-8")
    (repo_root / "config.json").write_text("{}", encoding="utf-8")
    
    # Ignored directories
    node_modules = repo_root / "node_modules"
    node_modules.mkdir()
    (node_modules / "index.js").write_text("console.log('ignored')", encoding="utf-8")
    
    # Sensitive files
    (repo_root / ".env").write_text("SECRET=123", encoding="utf-8")
    (repo_root / "key.pem").write_text("---BEGIN---", encoding="utf-8")

    service = FileDiscoveryService(repo_root)
    discovered = service.discover_files()
    
    paths = {f["relative_path"] for f in discovered}
    
    assert "main.py" in paths
    assert "config.json" in paths
    assert "node_modules/index.js" not in paths
    assert ".env" not in paths
    assert "key.pem" not in paths


def test_file_discovery_symlink_escape(tmp_path: Path):
    """Test that symlinks escaping the workspace are skipped."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("secret outside content", encoding="utf-8")
    
    # Symlink escaping root
    symlink_path = repo_root / "escape_link.txt"
    try:
        os.symlink(outside_file, symlink_path)
    except OSError:
        pytest.skip("Symlinks not supported by OS/user permissions")
        
    service = FileDiscoveryService(repo_root)
    discovered = service.discover_files()
    
    paths = {f["relative_path"] for f in discovered}
    assert "escape_link.txt" not in paths


def test_file_discovery_binary_detection(tmp_path: Path):
    """Test detection of binary files."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    
    # Text file
    (repo_root / "text.txt").write_text("hello", encoding="utf-8")
    
    # Binary file by extension
    (repo_root / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    
    # Binary file by content
    (repo_root / "unknown.dat").write_bytes(b"some \x00 binary data")
    
    service = FileDiscoveryService(repo_root)
    discovered = service.discover_files()
    
    file_map = {f["relative_path"]: f for f in discovered}
    
    assert file_map["text.txt"]["is_binary"] is False
    assert file_map["image.png"]["is_binary"] is True
    assert file_map["unknown.dat"]["is_binary"] is True


def test_file_discovery_size_limits(tmp_path: Path, monkeypatch):
    """Test oversized files and repo size limits."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    
    (repo_root / "small.txt").write_bytes(b"a" * 10)
    (repo_root / "large.txt").write_bytes(b"b" * 100)
    
    service = FileDiscoveryService(repo_root)
    # Monkeypatch max file size to 50 bytes
    service.max_file_size = 50
    
    discovered = service.discover_files()
    paths = {f["relative_path"] for f in discovered}
    
    assert "small.txt" in paths
    assert "large.txt" not in paths
    
    # Test max repo size
    service.max_repo_size = 5
    with pytest.raises(RuntimeError, match="Repository exceeds maximum"):
        service.discover_files()
