"""
app/modules/retrieval/search_service.py

Unified search facade — single entry point for all retrieval strategies.

Supports three modes:
- semantic: Vector search via Nomic embeddings + Qdrant
- keyword: BM25 lexical search
- hybrid: Combined via Reciprocal Rank Fusion

This is the only service that the router should interact with.
"""

from __future__ import annotations

import uuid
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.modules.retrieval.hybrid_search import HybridSearchService
from app.modules.retrieval.keyword_search import KeywordSearchService
from app.modules.retrieval.semantic_search import SemanticSearchService
from fastapi import HTTPException
from sqlalchemy import select
from app.modules.repositories.models import Repository
from app.modules.retrieval.keyword_index import INDEX_VERSION as CURRENT_CONTEXT_INDEX_VERSION

logger = get_logger(__name__)


class SearchService:
    """
    Unified search facade routing to the appropriate retrieval strategy.

    Usage:
        service = SearchService(db=session)
        results = await service.search(
            repository_id=repo_id,
            query="authentication middleware",
            mode="hybrid",
            top_k=10,
        )
    """

    def __init__(self, db: AsyncSession | None = None):
        self.db = db
        self._semantic_service = SemanticSearchService()
        self._keyword_service = KeywordSearchService(db=db)
        self._hybrid_service = HybridSearchService(db=db)

    async def search(
        self,
        repository_id: uuid.UUID,
        query: str,
        mode: Literal["semantic", "keyword", "hybrid"] = "hybrid",
        top_k: int = 10,
        debug: bool = False,
    ) -> dict[str, Any]:
        """
        Execute a search using the specified retrieval strategy.

        Args:
            repository_id: Repository to search within.
            query: User's search query.
            mode: Retrieval strategy ("semantic", "keyword", "hybrid").
            top_k: Number of results to return.
            debug: Include detailed ranking information.

        Returns:
            Dict with keys: results, mode, total_candidates.
        """
        logger.info(
            "search_request",
            repository_id=str(repository_id),
            mode=mode,
            top_k=top_k,
            query_length=len(query),
        )

        if self.db:
            repo = await self.db.scalar(select(Repository).where(Repository.id == repository_id))
            if repo and repo.index_version < CURRENT_CONTEXT_INDEX_VERSION:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "STALE_SEARCH_INDEX",
                        "message": "Repository must be re-ingested before searching.",
                        "repository_index_version": repo.index_version,
                        "required_index_version": CURRENT_CONTEXT_INDEX_VERSION
                    }
                )

        if mode == "semantic":
            results = await self._semantic_search(
                repository_id, query, top_k, debug
            )
        elif mode == "keyword":
            results = await self._keyword_search(
                repository_id, query, top_k, debug
            )
        elif mode == "hybrid":
            results = await self._hybrid_search(
                repository_id, query, top_k, debug
            )
        else:
            raise ValueError(f"Unknown search mode: {mode}")

        return {
            "results": results,
            "mode": mode,
            "total_candidates": len(results),
        }

    async def _semantic_search(
        self,
        repository_id: uuid.UUID,
        query: str,
        top_k: int,
        debug: bool,
    ) -> list[dict[str, Any]]:
        """Execute semantic-only search."""
        raw_results = await self._semantic_service.search(
            repository_id=repository_id,
            query=query,
            top_k=top_k,
        )

        results = []
        for i, r in enumerate(raw_results, start=1):
            result = {
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
                "rank": i,
                "source": "semantic",
                "class_name": getattr(r, "class_name", None),
                "parent_symbol": getattr(r, "parent_symbol", None),
                "module_name": getattr(r, "module_name", None),
                "context_path": getattr(r, "context_path", None),
            }
            if debug:
                result["semantic_rank"] = i
                result["semantic_score"] = r.score
            results.append(result)

        return results

    async def _keyword_search(
        self,
        repository_id: uuid.UUID,
        query: str,
        top_k: int,
        debug: bool,
    ) -> list[dict[str, Any]]:
        """Execute keyword-only search."""
        raw_results = await self._keyword_service.search(
            repository_id=repository_id,
            query=query,
            top_k=top_k,
        )

        results = []
        for i, r in enumerate(raw_results, start=1):
            result = {
                **r,
                "rank": i,
                "source": "keyword",
            }
            if debug:
                result["keyword_rank"] = i
                result["keyword_score"] = r.get("score", 0.0)
            results.append(result)

        return results

    async def _hybrid_search(
        self,
        repository_id: uuid.UUID,
        query: str,
        top_k: int,
        debug: bool,
    ) -> list[dict[str, Any]]:
        """Execute hybrid search (semantic + keyword + RRF)."""
        return await self._hybrid_service.search(
            repository_id=repository_id,
            query=query,
            top_k=top_k,
            debug=debug,
        )
