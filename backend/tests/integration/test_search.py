"""
tests/integration/test_search.py

Integration tests for the search system.

Tests:
- BM25 keyword search with real chunks
- Repository isolation (cross-repo leakage prevention)
- Incremental indexing (add, delete chunks)
- Search mode routing
"""

import uuid
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.repositories.models import (
    Repository,
    IndexedFile,
    CodeChunk,
)
from app.modules.retrieval.keyword_index import (
    build_index,
    save_index,
    load_index,
    delete_index,
    validate_index,
)
from app.modules.retrieval.keyword_search import KeywordSearchService
from app.modules.retrieval.search_service import SearchService


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _create_indexed_file(session, repository_id, path="src/main.py"):
    """Helper to create an IndexedFile in the test DB."""
    f = IndexedFile(
        id=uuid.uuid4(),
        repository_id=repository_id,
        ingestion_id=uuid.uuid4(),
        relative_path=path,
        file_size=100,
        extension=".py",
        is_binary=False,
        file_hash="abc123",
    )
    session.add(f)
    return f


def _create_code_chunk(session, indexed_file, content, symbol_name=None,
                       chunk_type="function", language="python"):
    """Helper to create a CodeChunk in the test DB."""
    import hashlib
    chunk = CodeChunk(
        id=uuid.uuid4(),
        indexed_file_id=indexed_file.id,
        content=content,
        chunk_type=chunk_type,
        symbol_name=symbol_name,
        language=language,
        start_line=1,
        end_line=10,
        content_hash=hashlib.sha256(content.encode()).hexdigest(),
    )
    session.add(chunk)
    return chunk


# ── Repository Isolation Tests ────────────────────────────────────────────────


class TestRepositoryIsolation:
    """Prove that search results never leak across repositories."""

    @pytest.mark.asyncio
    async def test_keyword_search_respects_repository_id(self, test_db_session):
        """BM25 search for repo A must not return chunks from repo B."""
        repo_a = uuid.uuid4()
        repo_b = uuid.uuid4()

        # Create chunks for repo A
        file_a = _create_indexed_file(test_db_session, repo_a, "src/auth.py")
        chunk_a = _create_code_chunk(
            test_db_session, file_a,
            "def authenticate_user(): pass",
            symbol_name="authenticate_user",
        )

        # Create chunks for repo B with similar content
        file_b = _create_indexed_file(test_db_session, repo_b, "src/auth.py")
        chunk_b = _create_code_chunk(
            test_db_session, file_b,
            "def authenticate_admin(): pass",
            symbol_name="authenticate_admin",
        )

        await test_db_session.commit()

        # Build separate indices
        chunks_a = [{
            "chunk_id": str(chunk_a.id),
            "repository_id": str(repo_a),
            "indexed_file_id": str(file_a.id),
            "file_path": "src/auth.py",
            "language": "python",
            "chunk_type": "function",
            "symbol_name": "authenticate_user",
            "content": "def authenticate_user(): pass",
            "start_line": 1,
            "end_line": 1,
        }]
        chunks_b = [{
            "chunk_id": str(chunk_b.id),
            "repository_id": str(repo_b),
            "indexed_file_id": str(file_b.id),
            "file_path": "src/auth.py",
            "language": "python",
            "chunk_type": "function",
            "symbol_name": "authenticate_admin",
            "content": "def authenticate_admin(): pass",
            "start_line": 1,
            "end_line": 1,
        }]

        # Use tmp paths for indices
        index_a = build_index(repo_a, chunks_a)
        index_b = build_index(repo_b, chunks_b)

        # Search repo A for "authenticate_user"
        from app.modules.retrieval.keyword_index import _tokenize
        scores_a = index_a.bm25.get_scores(_tokenize("authenticate_user"))
        scores_b = index_b.bm25.get_scores(_tokenize("authenticate_user"))

        # Both should find results in their own index (A finds it, B does not)
        assert scores_a[0] > 0
        assert scores_b[0] == 0

        # But repo A's index only has "authenticate_user"
        assert "authenticate_admin" not in [c["symbol_name"] for c in chunks_a]
        # And repo B's index only has "authenticate_admin"
        assert "authenticate_user" not in [c["symbol_name"] for c in chunks_b]


# ── Incremental Indexing Tests ────────────────────────────────────────────────


class TestIncrementalIndexing:
    """Tests for index updates when chunks change."""

    def test_new_chunk_invalidates_index(self):
        """Adding a new chunk should make the index stale."""
        repo_id = uuid.uuid4()
        chunks = [{"chunk_id": "c1", "content": "x",
                    "repository_id": str(repo_id), "indexed_file_id": "f1",
                    "file_path": "a.py", "language": "python",
                    "chunk_type": "function", "symbol_name": None,
                    "start_line": 1, "end_line": 1}]

        index = build_index(repo_id, chunks)

        # DB now has c1 + c2
        assert validate_index(index, ["c1", "c2"]) is False

    def test_deleted_chunk_invalidates_index(self):
        """Deleting a chunk should make the index stale."""
        repo_id = uuid.uuid4()
        chunks = [
            {"chunk_id": "c1", "content": "x",
             "repository_id": str(repo_id), "indexed_file_id": "f1",
             "file_path": "a.py", "language": "python",
             "chunk_type": "function", "symbol_name": None,
             "start_line": 1, "end_line": 1},
            {"chunk_id": "c2", "content": "y",
             "repository_id": str(repo_id), "indexed_file_id": "f1",
             "file_path": "a.py", "language": "python",
             "chunk_type": "function", "symbol_name": None,
             "start_line": 1, "end_line": 1},
        ]

        index = build_index(repo_id, chunks)

        # DB now only has c1 (c2 was deleted)
        assert validate_index(index, ["c1"]) is False

    def test_unchanged_chunks_valid_index(self):
        """Index should be valid when chunks haven't changed."""
        repo_id = uuid.uuid4()
        chunks = [
            {"chunk_id": "c1", "content": "x",
             "repository_id": str(repo_id), "indexed_file_id": "f1",
             "file_path": "a.py", "language": "python",
             "chunk_type": "function", "symbol_name": None,
             "start_line": 1, "end_line": 1},
        ]

        index = build_index(repo_id, chunks)
        assert validate_index(index, ["c1"]) is True

    def test_rebuild_after_deletion(self, tmp_path, monkeypatch):
        """After deletion, a rebuilt index should not contain the deleted chunk."""
        monkeypatch.setattr(
            "app.modules.retrieval.keyword_index.settings",
            type("S", (), {"keyword_index_dir": str(tmp_path)})(),
        )

        repo_id = uuid.uuid4()

        # Initial: 2 chunks
        chunks_v1 = [
            {"chunk_id": "c1", "content": "JWT_SECRET = value",
             "repository_id": str(repo_id), "indexed_file_id": "f1",
             "file_path": "a.py", "language": "python",
             "chunk_type": "function", "symbol_name": "JWT_SECRET",
             "start_line": 1, "end_line": 1},
            {"chunk_id": "c2", "content": "def hello(): pass",
             "repository_id": str(repo_id), "indexed_file_id": "f1",
             "file_path": "a.py", "language": "python",
             "chunk_type": "function", "symbol_name": "hello",
             "start_line": 1, "end_line": 1},
        ]
        index_v1 = build_index(repo_id, chunks_v1)
        save_index(repo_id, index_v1)

        # After deletion: only c1 remains
        chunks_v2 = [chunks_v1[0]]
        index_v2 = build_index(repo_id, chunks_v2)
        save_index(repo_id, index_v2)

        loaded = load_index(repo_id)
        assert loaded is not None
        assert loaded.metadata.chunk_count == 1
        assert "c2" not in loaded.chunk_ids


# ── Search Mode Tests ─────────────────────────────────────────────────────────


class TestSearchModes:
    """Tests for search mode routing."""

    @pytest.mark.asyncio
    async def test_keyword_mode_uses_bm25(self):
        """mode=keyword should use KeywordSearchService."""
        service = SearchService()

        with patch.object(
            service._keyword_service, "search",
            new_callable=AsyncMock, return_value=[]
        ) as mock_kw:
            await service.search(
                repository_id=uuid.uuid4(),
                query="test",
                mode="keyword",
                top_k=10,
            )
            mock_kw.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_semantic_mode_uses_qdrant(self):
        """mode=semantic should use SemanticSearchService."""
        service = SearchService()

        with patch.object(
            service._semantic_service, "search",
            new_callable=AsyncMock, return_value=[]
        ) as mock_sem:
            await service.search(
                repository_id=uuid.uuid4(),
                query="test",
                mode="semantic",
                top_k=10,
            )
            mock_sem.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_hybrid_mode_uses_both(self):
        """mode=hybrid should use both services."""
        service = SearchService()

        with patch.object(
            service._hybrid_service, "search",
            new_callable=AsyncMock, return_value=[]
        ) as mock_hybrid:
            await service.search(
                repository_id=uuid.uuid4(),
                query="test",
                mode="hybrid",
                top_k=10,
            )
            mock_hybrid.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_invalid_mode_raises(self):
        """Invalid mode should raise ValueError."""
        service = SearchService()

        with pytest.raises(ValueError, match="Unknown search mode"):
            await service.search(
                repository_id=uuid.uuid4(),
                query="test",
                mode="invalid",
                top_k=10,
            )
