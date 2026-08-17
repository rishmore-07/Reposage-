"""
tests/unit/test_hybrid_search.py

Unit tests for hybrid search: RRF fusion, deduplication, and fallback behavior.
"""

import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.retrieval.hybrid_search import HybridSearchService
from app.modules.retrieval.schemas import RetrievedChunk


def _make_retrieved_chunk(chunk_id, score=0.5, **kwargs):
    """Create a RetrievedChunk for mocking semantic search results."""
    return RetrievedChunk(
        chunk_id=chunk_id,
        repository_id="repo-1",
        indexed_file_id="file-1",
        code_symbol_id=None,
        file_path=f"src/{chunk_id}.py",
        language="python",
        chunk_type="function",
        symbol_name=chunk_id,
        start_line=1,
        end_line=10,
        content=f"def {chunk_id}(): pass",
        score=score,
        **kwargs,
    )


def _make_keyword_result(chunk_id, score=5.0):
    """Create a keyword search result dict."""
    return {
        "chunk_id": chunk_id,
        "repository_id": "repo-1",
        "indexed_file_id": "file-1",
        "code_symbol_id": None,
        "file_path": f"src/{chunk_id}.py",
        "language": "python",
        "chunk_type": "function",
        "symbol_name": chunk_id,
        "start_line": 1,
        "end_line": 10,
        "content": f"def {chunk_id}(): pass",
        "score": score,
    }


class TestHybridFusion:
    """Tests for hybrid search combining semantic and keyword results."""

    @pytest.mark.asyncio
    async def test_hybrid_combines_both_sources(self):
        """Hybrid search should include results from both systems."""
        service = HybridSearchService()

        with patch.object(service.semantic_service, "search", new_callable=AsyncMock) as mock_semantic, \
             patch.object(service.keyword_service, "search", new_callable=AsyncMock) as mock_keyword:

            mock_semantic.return_value = [
                _make_retrieved_chunk("A", score=0.9),
                _make_retrieved_chunk("B", score=0.7),
            ]
            mock_keyword.return_value = [
                _make_keyword_result("B", score=5.0),
                _make_keyword_result("C", score=3.0),
            ]

            results = await service.search(
                repository_id=uuid.uuid4(),
                query="test query",
                top_k=10,
            )

            chunk_ids = {r["chunk_id"] for r in results}
            assert "A" in chunk_ids  # semantic only
            assert "B" in chunk_ids  # both
            assert "C" in chunk_ids  # keyword only

    @pytest.mark.asyncio
    async def test_hybrid_deduplicates(self):
        """Chunks in both systems should appear only once."""
        service = HybridSearchService()

        with patch.object(service.semantic_service, "search", new_callable=AsyncMock) as mock_semantic, \
             patch.object(service.keyword_service, "search", new_callable=AsyncMock) as mock_keyword:

            mock_semantic.return_value = [
                _make_retrieved_chunk("SAME", score=0.8),
            ]
            mock_keyword.return_value = [
                _make_keyword_result("SAME", score=4.0),
            ]

            results = await service.search(
                repository_id=uuid.uuid4(),
                query="test",
                top_k=10,
            )

            assert len(results) == 1
            assert results[0]["chunk_id"] == "SAME"

    @pytest.mark.asyncio
    async def test_hybrid_debug_mode(self):
        """Debug mode should include ranking details."""
        service = HybridSearchService()

        with patch.object(service.semantic_service, "search", new_callable=AsyncMock) as mock_semantic, \
             patch.object(service.keyword_service, "search", new_callable=AsyncMock) as mock_keyword:

            mock_semantic.return_value = [_make_retrieved_chunk("A")]
            mock_keyword.return_value = [_make_keyword_result("A")]

            results = await service.search(
                repository_id=uuid.uuid4(),
                query="test",
                top_k=10,
                debug=True,
            )

            assert results[0]["semantic_rank"] is not None
            assert results[0]["keyword_rank"] is not None
            assert results[0]["rrf_score"] is not None


class TestHybridFallback:
    """Tests for graceful degradation when one system fails."""

    @pytest.mark.asyncio
    async def test_semantic_failure_returns_keyword(self):
        """If semantic search fails, return keyword results."""
        service = HybridSearchService()

        with patch.object(service.semantic_service, "search", new_callable=AsyncMock) as mock_semantic, \
             patch.object(service.keyword_service, "search", new_callable=AsyncMock) as mock_keyword:

            mock_semantic.side_effect = RuntimeError("Qdrant unreachable")
            mock_keyword.return_value = [
                _make_keyword_result("A"),
                _make_keyword_result("B"),
            ]

            results = await service.search(
                repository_id=uuid.uuid4(),
                query="test",
                top_k=10,
            )

            assert len(results) == 2
            assert results[0]["source"] == "keyword"

    @pytest.mark.asyncio
    async def test_keyword_failure_returns_semantic(self):
        """If keyword search fails, return semantic results."""
        service = HybridSearchService()

        with patch.object(service.semantic_service, "search", new_callable=AsyncMock) as mock_semantic, \
             patch.object(service.keyword_service, "search", new_callable=AsyncMock) as mock_keyword:

            mock_semantic.return_value = [
                _make_retrieved_chunk("A"),
                _make_retrieved_chunk("B"),
            ]
            mock_keyword.side_effect = RuntimeError("BM25 index not found")

            results = await service.search(
                repository_id=uuid.uuid4(),
                query="test",
                top_k=10,
            )

            assert len(results) == 2
            assert results[0]["source"] == "semantic"

    @pytest.mark.asyncio
    async def test_both_fail_raises_error(self):
        """If both systems fail, raise RuntimeError."""
        service = HybridSearchService()

        with patch.object(service.semantic_service, "search", new_callable=AsyncMock) as mock_semantic, \
             patch.object(service.keyword_service, "search", new_callable=AsyncMock) as mock_keyword:

            mock_semantic.side_effect = RuntimeError("Qdrant down")
            mock_keyword.side_effect = RuntimeError("BM25 missing")

            with pytest.raises(RuntimeError, match="Both search systems failed"):
                await service.search(
                    repository_id=uuid.uuid4(),
                    query="test",
                    top_k=10,
                )

    @pytest.mark.asyncio
    async def test_fallback_does_not_return_empty_silently(self):
        """System should not silently return empty on failure."""
        service = HybridSearchService()

        with patch.object(service.semantic_service, "search", new_callable=AsyncMock) as mock_semantic, \
             patch.object(service.keyword_service, "search", new_callable=AsyncMock) as mock_keyword:

            mock_semantic.side_effect = RuntimeError("down")
            mock_keyword.side_effect = RuntimeError("down")

            # Should raise, not return []
            with pytest.raises(RuntimeError):
                await service.search(
                    repository_id=uuid.uuid4(),
                    query="test",
                    top_k=10,
                )


class TestHybridTopK:
    """Tests for top_k limiting."""

    @pytest.mark.asyncio
    async def test_respects_top_k(self):
        """Should return at most top_k results."""
        service = HybridSearchService()

        with patch.object(service.semantic_service, "search", new_callable=AsyncMock) as mock_semantic, \
             patch.object(service.keyword_service, "search", new_callable=AsyncMock) as mock_keyword:

            mock_semantic.return_value = [
                _make_retrieved_chunk(f"s{i}", score=0.9 - i * 0.1) for i in range(10)
            ]
            mock_keyword.return_value = [
                _make_keyword_result(f"k{i}", score=10 - i) for i in range(10)
            ]

            results = await service.search(
                repository_id=uuid.uuid4(),
                query="test",
                top_k=5,
            )

            assert len(results) <= 5

class TestHybridReranking:
    """Tests for Phase 3G Retrieval Reranking."""
    
    @pytest.mark.asyncio
    async def test_reranker_disabled_flow(self):
        """When reranker is disabled, SearchService should use standard RRF top_k."""
        from app.modules.retrieval.search_service import SearchService
        service = SearchService()
        
        # Mock settings
        with patch("app.modules.retrieval.search_service.settings.reranker_enabled", False), \
             patch.object(service._hybrid_service, "search", new_callable=AsyncMock) as mock_hybrid:
            
            mock_hybrid.return_value = [
                _make_keyword_result("A", 10.0),
                _make_keyword_result("B", 8.0)
            ]
            
            results = await service.search(
                repository_id=uuid.uuid4(),
                query="test",
                mode="hybrid",
                top_k=5,
            )
            
            # Hybrid search should be called with top_k=5 because reranking is disabled
            mock_hybrid.assert_called_once()
            assert mock_hybrid.call_args[1]["top_k"] == 5
            assert len(results["results"]) == 2
            assert results["results"][0]["reranker_score"] is None

    @pytest.mark.asyncio
    async def test_reranker_enabled_flow(self):
        """When reranker is enabled, it reranks the RRF candidate pool."""
        from app.modules.retrieval.search_service import SearchService
        from app.modules.retrieval.schemas import RerankerCandidate
        
        with patch("app.modules.retrieval.search_service.settings.reranker_enabled", True), \
             patch("app.modules.retrieval.search_service.settings.reranker_candidate_k", 30), \
             patch("app.modules.retrieval.reranker_service.settings.reranker_enabled", True):
             
            service = SearchService()
            # Must re-init service to pick up mocked enabled setting in _reranker_service
            
            with patch.object(service._hybrid_service, "search", new_callable=AsyncMock) as mock_hybrid, \
                 patch.object(service._reranker_service, "rerank", new_callable=AsyncMock) as mock_rerank:
                
                # RRF returns 2 candidates
                mock_hybrid.return_value = [
                    _make_keyword_result("A", 10.0),
                    _make_keyword_result("B", 8.0)
                ]
                
                # Mock the reranker reversing the order
                mock_rerank.return_value = (
                    [
                        RerankerCandidate(
                            chunk_id="B",
                            repository_id="repo-1",
                            file_path="src/B.py",
                            language="python",
                            chunk_type="function",
                            content="def B(): pass",
                            reranker_score=0.9
                        ),
                        RerankerCandidate(
                            chunk_id="A",
                            repository_id="repo-1",
                            file_path="src/A.py",
                            language="python",
                            chunk_type="function",
                            content="def A(): pass",
                            reranker_score=0.1
                        )
                    ],
                    50.0  # latency ms
                )
                
                results = await service.search(
                    repository_id=uuid.uuid4(),
                    query="test",
                    mode="hybrid",
                    top_k=5,
                    debug=True
                )
                
                # Hybrid search should be called with candidate_k=30
                mock_hybrid.assert_called_once()
                assert mock_hybrid.call_args[1]["top_k"] == 30
                
                # Reranker should have been called
                mock_rerank.assert_called_once()
                
                # Results should reflect the new order
                assert results["results"][0]["chunk_id"] == "B"
                assert results["results"][1]["chunk_id"] == "A"
                
                # Original rrf scores / keyword scores should be preserved from the original dictionaries
                assert results["results"][0]["reranker_score"] == 0.9
                
                # Latency tracked
                assert results["reranker_latency_ms"] == 50.0

    @pytest.mark.asyncio
    async def test_reranker_failure_fallback(self):
        """When reranker fails, gracefully degrade to RRF results without throwing."""
        from app.modules.retrieval.search_service import SearchService
        
        with patch("app.modules.retrieval.search_service.settings.reranker_enabled", True), \
             patch("app.modules.retrieval.search_service.settings.reranker_candidate_k", 30), \
             patch("app.modules.retrieval.reranker_service.settings.reranker_enabled", True):
             
            service = SearchService()
            
            with patch.object(service._hybrid_service, "search", new_callable=AsyncMock) as mock_hybrid, \
                 patch.object(service._reranker_service, "rerank", new_callable=AsyncMock) as mock_rerank:
                
                # RRF returns 2 candidates
                mock_hybrid.return_value = [
                    _make_keyword_result("A", 10.0),
                    _make_keyword_result("B", 8.0)
                ]
                
                # Reranker throws
                mock_rerank.side_effect = RuntimeError("Mock reranker explosion")
                
                # Should not raise exception
                results = await service.search(
                    repository_id=uuid.uuid4(),
                    query="test",
                    mode="hybrid",
                    top_k=5,
                )
                
                # Fallback to RRF order
                assert len(results["results"]) == 2
                assert results["results"][0]["chunk_id"] == "A"
                assert results["results"][1]["chunk_id"] == "B"
                assert results["results"][0]["reranker_score"] is None
