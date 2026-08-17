"""
app/modules/retrieval/hybrid_search.py

Hybrid search orchestrator combining semantic and keyword retrieval via RRF.

Graceful degradation:
- If Qdrant/semantic search fails → returns keyword results only
- If BM25/keyword search fails → returns semantic results only
- If both fail → raises a clean error

This module never puts retrieval algorithms inside route handlers.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.modules.retrieval.keyword_search import KeywordSearchService
from app.modules.retrieval.rrf import FusedResult, reciprocal_rank_fusion
from app.modules.retrieval.semantic_search import SemanticSearchService

logger = get_logger(__name__)


class HybridSearchService:
    """
    Combines semantic vector search and BM25 keyword search using
    Reciprocal Rank Fusion (RRF).

    Retrieves a larger candidate pool from each system, then fuses
    and returns the final top-K results.
    """

    def __init__(self, db: AsyncSession | None = None):
        self.semantic_service = SemanticSearchService()
        self.keyword_service = KeywordSearchService(db=db)

    async def search(
        self,
        repository_id: uuid.UUID,
        query: str,
        top_k: int = 10,
        semantic_k: int | None = None,
        keyword_k: int | None = None,
        rrf_k: int | None = None,
        debug: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Perform hybrid search combining semantic and keyword retrieval.

        Args:
            repository_id: Repository to search within.
            query: User's search query.
            top_k: Number of final results to return.
            semantic_k: Candidate pool size for semantic search.
            keyword_k: Candidate pool size for keyword search.
            rrf_k: RRF fusion constant.
            debug: If True, include detailed ranking info in results.

        Returns:
            List of result dicts sorted by RRF score.

        Raises:
            RuntimeError: If both retrieval systems fail.
        """
        _semantic_k = semantic_k or settings.semantic_candidate_k
        _keyword_k = keyword_k or settings.keyword_candidate_k
        _rrf_k = rrf_k or settings.rrf_k

        semantic_results = []
        keyword_results = []
        semantic_error = None
        keyword_error = None

        # Attempt semantic search
        try:
            raw_semantic = await self.semantic_service.search(
                repository_id=repository_id,
                query=query,
                top_k=_semantic_k,
            )
            # Convert RetrievedChunk objects to dicts
            semantic_results = [
                {
                    "chunk_id": r.chunk_id,
                    "repository_id": r.repository_id,
                    "indexed_file_id": r.indexed_file_id,
                    "code_symbol_id": r.code_symbol_id,
                    "file_path": r.file_path,
                    "language": r.language,
                    "chunk_type": r.chunk_type,
                    "symbol_name": r.symbol_name,
                    "start_line": r.start_line,
                    "end_line": r.end_line,
                    "content": r.content,
                    "score": r.score,
                }
                for r in raw_semantic
            ]
        except Exception as e:
            semantic_error = e
            logger.warning(
                "hybrid_search_semantic_failed",
                repository_id=str(repository_id),
                error=str(e),
            )

        # Attempt keyword search
        try:
            keyword_results = await self.keyword_service.search(
                repository_id=repository_id,
                query=query,
                top_k=_keyword_k,
            )
        except Exception as e:
            keyword_error = e
            logger.warning(
                "hybrid_search_keyword_failed",
                repository_id=str(repository_id),
                error=str(e),
            )

        # Handle failure cases
        if semantic_error and keyword_error:
            raise RuntimeError(
                f"Both search systems failed. "
                f"Semantic: {semantic_error}. "
                f"Keyword: {keyword_error}."
            )

        if semantic_error:
            # Fallback to keyword-only results
            logger.info(
                "hybrid_search_fallback_keyword",
                repository_id=str(repository_id),
            )
            return self._format_single_source_results(
                keyword_results, source="keyword", top_k=top_k
            )

        if keyword_error:
            # Fallback to semantic-only results
            logger.info(
                "hybrid_search_fallback_semantic",
                repository_id=str(repository_id),
            )
            return self._format_single_source_results(
                semantic_results, source="semantic", top_k=top_k
            )

        # Both succeeded — perform RRF fusion
        fused = reciprocal_rank_fusion(
            semantic_results=semantic_results,
            keyword_results=keyword_results,
            k=_rrf_k,
        )

        # Convert FusedResult to result dicts
        results = []
        for fr in fused[:top_k]:
            result = {
                "chunk_id": fr.chunk_id,
                "repository_id": fr.repository_id,
                "indexed_file_id": fr.indexed_file_id,
                "code_symbol_id": fr.code_symbol_id,
                "file_path": fr.file_path,
                "language": fr.language,
                "chunk_type": fr.chunk_type,
                "symbol_name": fr.symbol_name,
                "start_line": fr.start_line,
                "end_line": fr.end_line,
                "content": fr.content,
                "score": fr.rrf_score,
                "rank": fr.fused_rank,
                "source": "hybrid",
            }
            if debug:
                result["semantic_rank"] = fr.semantic_rank
                result["keyword_rank"] = fr.keyword_rank
                result["semantic_score"] = fr.semantic_score
                result["keyword_score"] = fr.keyword_score
                result["rrf_score"] = fr.rrf_score
            results.append(result)

        logger.info(
            "hybrid_search_completed",
            repository_id=str(repository_id),
            semantic_candidates=len(semantic_results),
            keyword_candidates=len(keyword_results),
            fused_total=len(fused),
            returned=len(results),
        )

        return results

    @staticmethod
    def _format_single_source_results(
        results: list[dict[str, Any]],
        source: str,
        top_k: int,
    ) -> list[dict[str, Any]]:
        """Format single-source results with rank and source info."""
        formatted = []
        for i, result in enumerate(results[:top_k], start=1):
            formatted.append({
                **result,
                "rank": i,
                "source": source,
            })
        return formatted
