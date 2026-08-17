from app.core.config import settings
from app.modules.embeddings.base import EmbeddingProvider
from app.modules.embeddings.providers.ollama import OllamaEmbeddingProvider
# from app.modules.embeddings.providers.gemini import GeminiEmbeddingProvider # Future phase

class EmbeddingFactory:
    @staticmethod
    def get_provider() -> EmbeddingProvider:
        provider_name = settings.embedding_provider
        
        if provider_name == "ollama":
            return OllamaEmbeddingProvider(
                base_url=settings.embedding_base_url,
                model=settings.embedding_model,
                dimension=settings.embedding_dimension
            )
        elif provider_name == "gemini":
            raise NotImplementedError("Gemini embedding provider will be implemented in a future phase.")
        else:
            raise ValueError(f"Unknown embedding provider: {provider_name}")
