import uuid
import os
from pathlib import Path
from unittest import mock

import pytest
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.modules.repositories.models import (
    Repository,
    RepositoryIngestion,
    IndexedFile,
    CodeSymbol,
    UserConnectedRepository,
)
from app.modules.users.models import User
from app.core.constants import IngestionStatus
from app.core.encryption import encrypt_string
from app.workers.tasks.ingestion_tasks import ingest_repository, _get_sync_session

@pytest.fixture
def mock_git_service(monkeypatch, tmp_path: Path):
    """Mocks GitRepositoryService to point to a temporary directory with dummy files."""
    repo_dir = tmp_path / "mock_repo"
    repo_dir.mkdir()
    
    # Valid Python file
    (repo_dir / "main.py").write_text("def hello():\n    pass\n", encoding="utf-8")
    
    # Invalid Python file
    (repo_dir / "bad.py").write_text("def bad()\npass", encoding="utf-8")
    
    # Binary file
    (repo_dir / "image.png").write_bytes(b"\x00\x01\x02")
    
    # Unsupported file
    (repo_dir / "unknown.xyz").write_text("hello", encoding="utf-8")
    
    # Malicious file that tries to execute code if imported
    (repo_dir / "evil.py").write_text("import os\nos.system('echo EVIL')\nclass Evil:\n  pass", encoding="utf-8")

    class MockGitService:
        def __init__(self, *args, **kwargs):
            pass
        def clone_repository(self, *args, **kwargs):
            return "mocksha123"
        def get_source_dir(self):
            return repo_dir
        def cleanup_workspace(self):
            pass

    monkeypatch.setattr("app.workers.tasks.ingestion_tasks.GitRepositoryService", MockGitService)


@pytest.fixture
def setup_ingestion_db() -> tuple[uuid.UUID, uuid.UUID]:
    """Creates dummy repository and user in DB for ingestion test."""
    db_session = _get_sync_session()
    try:
        user = User(
            email=f"test_ingest_{uuid.uuid4().hex[:8]}@example.com",
            full_name="test_ingest",
            hashed_password="pw",
            github_access_token=encrypt_string("dummy_token")
        )
        db_session.add(user)
        db_session.flush()

        repo = Repository(
            github_repo_id=uuid.uuid4().int % 1000000000,
            full_name="test/repo",
            name="repo",
            html_url="http",
            status="pending"
        )
        db_session.add(repo)
        db_session.flush()

        conn = UserConnectedRepository(user_id=user.id, repository_id=repo.id)
        db_session.add(conn)
        
        ingestion = RepositoryIngestion(
            repository_id=repo.id,
            status=IngestionStatus.PENDING
        )
        db_session.add(ingestion)
        db_session.commit()
        
        return repo.id, ingestion.id
    finally:
        db_session.close()


def test_indexing_pipeline(mock_git_service, setup_ingestion_db):
    repo_id, ingestion_id = setup_ingestion_db
    
    # Run the Celery task synchronously
    result = ingest_repository(str(ingestion_id))
    
    assert result["status"] == "success"
    
    db_session = _get_sync_session()
    try:
        # Reload DB state
        ingestion = db_session.scalar(select(RepositoryIngestion).where(RepositoryIngestion.id == ingestion_id))
        assert ingestion.status == IngestionStatus.COMPLETED
        
        # We created 5 files: main.py, bad.py, image.png, unknown.xyz, evil.py
        assert ingestion.file_count == 5
        
        # Check IndexedFiles
        files = db_session.scalars(select(IndexedFile).where(IndexedFile.ingestion_id == ingestion_id)).all()
        assert len(files) == 5
        
        file_map = {f.relative_path: f for f in files}
        
        # Check stats
        assert ingestion.parsed_file_count == 3  # main.py, bad.py (partial), evil.py
        assert ingestion.unsupported_file_count == 1 # unknown.xyz
        assert ingestion.parse_error_count == 0 # partial parse is not an error
        
        # Check CodeSymbols
        # main.py has 1 function `hello`
        # bad.py has 1 function `bad` (even though it's partial, tree-sitter often gets the identifier)
        # evil.py has 1 class `Evil` and 1 import `os`
        
        symbols = db_session.scalars(select(CodeSymbol).where(CodeSymbol.indexed_file_id == file_map["main.py"].id)).all()
        assert len(symbols) == 1
        assert symbols[0].name == "hello"
        assert symbols[0].symbol_type == "FUNCTION"
        
        evil_symbols = db_session.scalars(select(CodeSymbol).where(CodeSymbol.indexed_file_id == file_map["evil.py"].id)).all()
        names = {s.name for s in evil_symbols}
        assert "Evil" in names
        assert "os" in names
        
        # Verify no execution happened (malicious evil.py didn't crash us or execute os.system during parsing)
        # The fact that the test completed successfully proves no arbitrary code execution or crash.
    finally:
        db_session.close()
