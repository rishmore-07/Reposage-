import uuid
from typing import List

from app.modules.embeddings.factory import EmbeddingFactory
from app.modules.vectorstore.qdrant_service import QdrantService
from app.modules.retrieval.schemas import RetrievedChunk

class SemanticSearchService:
    def __init__(self):
        self.embedding_provider = EmbeddingFactory.get_provider()
        self.qdrant_service = QdrantService()

    async def search(self, repository_id: uuid.UUID, query: str, top_k: int = 10) -> List[RetrievedChunk]:
        """
        Embed the query and retrieve relevant code chunks for the given repository.
        """
        query_vector = await self.embedding_provider.embed_query(query)
        
        # Search Qdrant
        raw_results = await self.qdrant_service.search(
            repository_id=repository_id,
            query_vector=query_vector,
            top_k=top_k
        )
        
        results = []
        for raw in raw_results:
            results.append(RetrievedChunk(**raw))
            
        return results
