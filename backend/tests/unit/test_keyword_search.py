"""
tests/unit/test_keyword_search.py

Unit tests for BM25 keyword search.

Tests BM25 ranking, repository isolation, tokenization,
and index lifecycle without requiring external services.
"""

import uuid
import pytest
from app.modules.retrieval.keyword_index import (
    build_index,
    build_searchable_text,
    _tokenize,
    validate_index,
    save_index,
    load_index,
    delete_index,
    PersistedIndex,
    IndexMetadata,
    INDEX_VERSION,
)


def _make_chunk(chunk_id, content, file_path="src/test.py", language="python",
                chunk_type="function", symbol_name=None, repository_id="repo-1"):
    """Helper to create a chunk data dict."""
    return {
        "chunk_id": chunk_id,
        "repository_id": repository_id,
        "indexed_file_id": "file-1",
        "code_symbol_id": None,
        "file_path": file_path,
        "language": language,
        "chunk_type": chunk_type,
        "symbol_name": symbol_name,
        "content": content,
        "start_line": 1,
        "end_line": 10,
    }


class TestTokenizer:
    """Tests for the BM25 tokenizer."""

    def test_basic_tokenization(self):
        tokens = _tokenize("def hello_world(): pass")
        assert "def" in tokens
        assert "hello_world" in tokens
        assert "pass" in tokens

    def test_preserves_underscores(self):
        """Underscores in identifiers should be preserved."""
        tokens = _tokenize("JWT_SECRET = 'value'")
        assert "jwt_secret" in tokens

    def test_lowercases(self):
        tokens = _tokenize("AuthService UserModel")
        assert "authservice" in tokens
        assert "usermodel" in tokens

    def test_splits_on_punctuation(self):
        tokens = _tokenize("def func(arg1, arg2):")
        assert "func" in tokens
        assert "arg1" in tokens
        assert "arg2" in tokens

    def test_empty_string(self):
        assert _tokenize("") == []

    def test_only_punctuation(self):
        assert _tokenize("... --- !!!") == []


class TestSearchableText:
    """Tests for building searchable BM25 document text."""

    def test_includes_metadata(self):
        chunk = _make_chunk("1", "def hello(): pass",
                            file_path="src/auth.py",
                            symbol_name="hello")
        text = build_searchable_text(chunk)

        assert "File: src/auth.py" in text
        assert "Language: python" in text
        assert "Symbol: hello" in text
        assert "def hello(): pass" in text

    def test_missing_symbol_name(self):
        chunk = _make_chunk("1", "x = 1", symbol_name=None)
        text = build_searchable_text(chunk)
        assert "Symbol:" not in text


class TestBM25Ranking:
    """Tests for BM25 ranking correctness."""

    def test_exact_identifier_ranked_highly(self):
        """Exact identifier queries should strongly match."""
        repo_id = uuid.uuid4()
        chunks = [
            _make_chunk("c1", "JWT_SECRET = 'mysecret'", symbol_name="JWT_SECRET"),
            _make_chunk("c2", "def process_data(): return 42"),
            _make_chunk("c3", "class UserModel: pass"),
        ]

        index = build_index(repo_id, chunks)
        query_tokens = _tokenize("JWT_SECRET")
        scores = index.bm25.get_scores(query_tokens)

        # JWT_SECRET chunk should have the highest score
        assert scores[0] > scores[1]
        assert scores[0] > scores[2]

    def test_function_name_ranking(self):
        """Function name queries should match the right chunk."""
        repo_id = uuid.uuid4()
        chunks = [
            _make_chunk("c1", "def authenticate_user(u, p): pass", symbol_name="authenticate_user"),
            _make_chunk("c2", "def process_payment(): pass", symbol_name="process_payment"),
            _make_chunk("c3", "def send_email(): pass", symbol_name="send_email"),
        ]

        index = build_index(repo_id, chunks)
        query_tokens = _tokenize("authenticate_user")
        scores = index.bm25.get_scores(query_tokens)

        assert scores[0] > scores[1]
        assert scores[0] > scores[2]

    def test_natural_language_query(self):
        """Natural language queries should find relevant terms."""
        repo_id = uuid.uuid4()
        chunks = [
            _make_chunk("c1",
                "def authenticate_user(username, password):\n"
                "    # verify login credentials\n"
                "    token = create_jwt(username)",
                symbol_name="authenticate_user"),
            _make_chunk("c2", "def format_date(d): return str(d)", symbol_name="format_date"),
        ]

        index = build_index(repo_id, chunks)
        query_tokens = _tokenize("user authentication login")
        scores = index.bm25.get_scores(query_tokens)

        # Authentication chunk should score higher
        assert scores[0] > scores[1]

    def test_file_path_search(self):
        """Searching for file path components should work."""
        repo_id = uuid.uuid4()
        chunks = [
            _make_chunk("c1", "class AuthService: pass",
                        file_path="backend/auth/service.py"),
            _make_chunk("c2", "class DataService: pass",
                        file_path="backend/data/service.py"),
        ]

        index = build_index(repo_id, chunks)
        query_tokens = _tokenize("auth service")
        scores = index.bm25.get_scores(query_tokens)

        # Both have "service" but only c1 has "auth"
        assert scores[0] > scores[1]


class TestBM25EmptyAndEdgeCases:
    """Tests for edge cases in BM25 search."""

    def test_empty_query(self):
        """Empty query should produce zero scores."""
        repo_id = uuid.uuid4()
        chunks = [_make_chunk("c1", "some content")]
        index = build_index(repo_id, chunks)

        query_tokens = _tokenize("")
        # Empty tokens list
        assert query_tokens == []

    def test_no_matching_terms(self):
        """Query with no matching terms should produce zero scores."""
        repo_id = uuid.uuid4()
        chunks = [_make_chunk("c1", "def hello(): pass")]
        index = build_index(repo_id, chunks)

        query_tokens = _tokenize("zzzznonexistent")
        scores = index.bm25.get_scores(query_tokens)
        assert scores[0] == 0.0

    def test_empty_corpus(self):
        """Building index with no chunks should not crash."""
        repo_id = uuid.uuid4()
        index = build_index(repo_id, [])
        assert index.metadata.chunk_count == 0


class TestIndexValidation:
    """Tests for index staleness detection."""

    def test_valid_index(self):
        repo_id = uuid.uuid4()
        chunks = [
            _make_chunk("c1", "content1"),
            _make_chunk("c2", "content2"),
        ]
        index = build_index(repo_id, chunks)

        assert validate_index(index, ["c1", "c2"]) is True

    def test_stale_index_missing_chunk(self):
        """Index should be invalid if a new chunk was added."""
        repo_id = uuid.uuid4()
        chunks = [_make_chunk("c1", "content1")]
        index = build_index(repo_id, chunks)

        # DB now has c1 and c2, but index only has c1
        assert validate_index(index, ["c1", "c2"]) is False

    def test_stale_index_extra_chunk(self):
        """Index should be invalid if a chunk was deleted."""
        repo_id = uuid.uuid4()
        chunks = [
            _make_chunk("c1", "content1"),
            _make_chunk("c2", "content2"),
        ]
        index = build_index(repo_id, chunks)

        # DB now only has c1
        assert validate_index(index, ["c1"]) is False


class TestIndexPersistence:
    """Tests for index save/load lifecycle."""

    def test_save_and_load(self, tmp_path, monkeypatch):
        """Index should survive a save/load cycle."""
        monkeypatch.setattr(
            "app.modules.retrieval.keyword_index.settings",
            type("S", (), {"keyword_index_dir": str(tmp_path)})(),
        )

        repo_id = uuid.uuid4()
        chunks = [
            _make_chunk("c1", "def hello(): pass"),
            _make_chunk("c2", "class World: pass"),
        ]

        index = build_index(repo_id, chunks)
        save_index(repo_id, index)

        loaded = load_index(repo_id)
        assert loaded is not None
        assert loaded.metadata.chunk_count == 2
        assert loaded.metadata.repository_id == str(repo_id)
        assert set(loaded.chunk_ids) == {"c1", "c2"}

    def test_load_nonexistent(self, tmp_path, monkeypatch):
        """Loading a non-existent index should return None."""
        monkeypatch.setattr(
            "app.modules.retrieval.keyword_index.settings",
            type("S", (), {"keyword_index_dir": str(tmp_path)})(),
        )

        result = load_index(uuid.uuid4())
        assert result is None

    def test_delete_index(self, tmp_path, monkeypatch):
        """Deleting an index should remove the file."""
        monkeypatch.setattr(
            "app.modules.retrieval.keyword_index.settings",
            type("S", (), {"keyword_index_dir": str(tmp_path)})(),
        )

        repo_id = uuid.uuid4()
        chunks = [_make_chunk("c1", "content")]
        index = build_index(repo_id, chunks)
        save_index(repo_id, index)

        assert delete_index(repo_id) is True
        assert load_index(repo_id) is None

    def test_delete_nonexistent(self, tmp_path, monkeypatch):
        """Deleting a non-existent index should return False."""
        monkeypatch.setattr(
            "app.modules.retrieval.keyword_index.settings",
            type("S", (), {"keyword_index_dir": str(tmp_path)})(),
        )
        assert delete_index(uuid.uuid4()) is False


class TestRepositoryIsolation:
    """Tests proving cross-repository isolation in BM25."""

    def test_separate_indices_per_repository(self):
        """Each repository gets its own BM25 index."""
        repo1 = uuid.uuid4()
        repo2 = uuid.uuid4()

        chunks1 = [_make_chunk("c1", "JWT_SECRET = 'secret'", repository_id=str(repo1))]
        chunks2 = [_make_chunk("c2", "PAYMENT_KEY = 'key'", repository_id=str(repo2))]

        index1 = build_index(repo1, chunks1)
        index2 = build_index(repo2, chunks2)

        # Search for JWT_SECRET in repo1's index
        scores1 = index1.bm25.get_scores(_tokenize("JWT_SECRET"))
        assert scores1[0] > 0

        # Search for JWT_SECRET in repo2's index — should not find it
        scores2 = index2.bm25.get_scores(_tokenize("JWT_SECRET"))
        assert scores2[0] == 0.0

    def test_index_metadata_has_repository_id(self):
        """Each index stores its repository_id for validation."""
        repo_id = uuid.uuid4()
        chunks = [_make_chunk("c1", "content")]
        index = build_index(repo_id, chunks)

        assert index.metadata.repository_id == str(repo_id)
