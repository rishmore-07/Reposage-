import httpx
from typing import List
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.logging import get_logger
from app.modules.embeddings.base import EmbeddingProvider

logger = get_logger(__name__)

class OllamaEmbeddingProvider(EmbeddingProvider):
    def __init__(self, base_url: str, model: str, dimension: int):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._dimension = dimension
        self.api_url = f"{self.base_url}/api/embed"
        
    @property
    def dimension(self) -> int:
        return self._dimension

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError))
    )
    async def _call_ollama(self, texts: List[str]) -> List[List[float]]:
        # Using httpx.AsyncClient without a context manager for one-off calls is fine,
        # but better to use a short-lived client.
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                self.api_url,
                json={
                    "model": self.model,
                    "input": texts
                }
            )
            response.raise_for_status()
            data = response.json()
            
            if "embeddings" not in data:
                raise ValueError("Malformed response from Ollama: 'embeddings' key missing")
                
            embeddings = data["embeddings"]
            
            if not embeddings:
                return []
                
            if len(embeddings[0]) != self.dimension:
                raise ValueError(f"Embedding dimension mismatch. Expected {self.dimension}, got {len(embeddings[0])}")
                
            return embeddings

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        
        try:
            return await self._call_ollama(texts)
        except Exception as e:
            logger.error(f"Failed to embed documents with Ollama: {e}")
            raise RuntimeError("Embedding service unavailable") from e

    async def embed_query(self, text: str) -> List[float]:
        try:
            embeddings = await self._call_ollama([text])
            if not embeddings:
                raise ValueError("Empty embedding returned for query")
            return embeddings[0]
        except Exception as e:
            logger.error(f"Failed to embed query with Ollama: {e}")
            raise RuntimeError("Embedding service unavailable") from e
