"""
app/modules/retrieval/reranker_service.py

Service layer for retrieval reranking.
Responsible for resolving and invoking the configured reranker provider.
"""

from __future__ import annotations

import time

from app.core.config import settings
from app.core.logging import get_logger
from app.modules.retrieval.reranker import MockRerankerProvider, RerankerProvider
from app.modules.retrieval.schemas import RerankerCandidate

logger = get_logger(__name__)


class RerankerService:
    """
    Service responsible for orchestrating the reranking of candidate chunks.
    Resolves the appropriate provider based on configuration.
    """

    def __init__(self) -> None:
        self.enabled = settings.reranker_enabled
        self.provider_name = settings.reranker_provider
        self._provider: RerankerProvider | None = None

        if self.enabled:
            self._provider = self._resolve_provider(self.provider_name)

    def _resolve_provider(self, provider_name: str) -> RerankerProvider:
        """Resolve the provider from config."""
        if provider_name == "mock":
            return MockRerankerProvider()
        else:
            # Future providers (e.g., cross_encoder) can be registered here.
            logger.warning(
                "unknown_reranker_provider_fallback",
                requested=provider_name,
                fallback="mock"
            )
            return MockRerankerProvider()

    async def rerank(
        self, query: str, candidates: list[RerankerCandidate], top_k: int
    ) -> tuple[list[RerankerCandidate], float]:
        """
        Rerank a list of candidates.

        Args:
            query: The search query string.
            candidates: The list of candidate chunks from RRF.
            top_k: The final number of results to return.

        Returns:
            A tuple of (reranked_candidates, latency_ms).
        """
        if not self.enabled or not self._provider or not candidates:
            # If disabled or empty, return as is (truncated to top_k)
            return candidates[:top_k], 0.0

        start_time = time.perf_counter()
        
        # Invoke the underlying provider
        reranked = await self._provider.rerank(query, candidates, top_k)
        
        latency_ms = (time.perf_counter() - start_time) * 1000.0
        
        return reranked, latency_ms
