"""
app/ai/embeddings/base_embedder.py

Abstract interface for text/code embedding providers.

Implement concrete embedders in sibling files:
- gemini_embedder.py  — Google Gemini text-embedding-004
- openai_embedder.py  — OpenAI text-embedding-3-small

The factory function in __init__.py selects the implementation based on
config.ai_embedding_provider, allowing hot-swapping with a single config change.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseEmbedder(ABC):
    """Abstract interface for text/code embedding providers."""

    @abstractmethod
    async def embed_text(self, text: str) -> list[float]:
        """
        Embed a single text string into a dense float vector.

        Args:
            text: The text to embed. May be code, documentation, or prose.

        Returns:
            A list of floats representing the embedding vector.
            Dimensionality is provider-specific (e.g., 768 for Gemini).
        """

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Embed multiple texts in a single API call for efficiency.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors, one per input text.
        """

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Return the number of dimensions in this embedder's output vectors."""
