from abc import ABC, abstractmethod
from typing import List

class EmbeddingProvider(ABC):
    """
    Abstract interface for generating embeddings.
    Allows swapping between Ollama, Gemini, OpenAI, etc.
    """

    @abstractmethod
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Embed a batch of documents.
        Returns a list of vectors, one for each input text.
        """
        pass

    @abstractmethod
    async def embed_query(self, text: str) -> List[float]:
        """
        Embed a single search query.
        """
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """
        The dimensionality of the embeddings produced by this provider.
        """
        pass
