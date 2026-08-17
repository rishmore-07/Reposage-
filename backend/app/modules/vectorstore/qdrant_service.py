import uuid
from typing import List, Dict, Any
from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as qmodels

from app.core.config import settings
from app.core.logging import get_logger
from app.modules.vectorstore.schemas import VectorPayload

logger = get_logger(__name__)

class QdrantService:
    """Service to interact with Qdrant vector database."""
    
    def __init__(self):
        self.client = AsyncQdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            timeout=60.0
        )
        self.collection_name = settings.qdrant_collection
        self.dimension = settings.embedding_dimension

    async def initialize_collection(self):
        """Ensure the collection exists and has the correct configuration."""
        try:
            collections = await self.client.get_collections()
            exists = any(c.name == self.collection_name for c in collections.collections)
            
            if exists:
                # Validate dimension
                collection_info = await self.client.get_collection(self.collection_name)
                # Qdrant collections config vectors can be a dict or a VectorParams object
                if isinstance(collection_info.config.params.vectors, qmodels.VectorParams):
                    actual_dim = collection_info.config.params.vectors.size
                else:
                    # In case of named vectors
                    actual_dim = collection_info.config.params.vectors.get("").size if collection_info.config.params.vectors else 0
                    
                if actual_dim != self.dimension:
                    raise ValueError(f"Collection '{self.collection_name}' has dimension {actual_dim}, but {self.dimension} is required.")
                logger.info(f"Qdrant collection '{self.collection_name}' exists and validated.")
            else:
                logger.info(f"Creating Qdrant collection '{self.collection_name}' with dimension {self.dimension}.")
                await self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=qmodels.VectorParams(
                        size=self.dimension,
                        distance=qmodels.Distance.COSINE
                    )
                )
                
                # Create index for repository_id to speed up search filtering
                await self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name="repository_id",
                    field_schema=qmodels.PayloadSchemaType.KEYWORD,
                )
                
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant collection: {e}")
            raise

    async def upsert_vectors(self, vectors: List[List[float]], payloads: List[VectorPayload]):
        """
        Upsert vectors into Qdrant.
        Uses the deterministic UUID from chunk_id as the Qdrant point ID.
        """
        if not vectors or not payloads:
            return
            
        if len(vectors) != len(payloads):
            raise ValueError("Number of vectors must match number of payloads")
            
        points = []
        for i, (vector, payload) in enumerate(zip(vectors, payloads)):
            # Qdrant requires UUID or Unsigned Integer. chunk_id is a UUID string.
            points.append(qmodels.PointStruct(
                id=payload.chunk_id,
                vector=vector,
                payload=payload.model_dump()
            ))
            
        await self.client.upsert(
            collection_name=self.collection_name,
            points=points
        )
        
    async def search(self, repository_id: uuid.UUID, query_vector: List[float], top_k: int = 10) -> List[VectorPayload]:
        """
        Search for similar code chunks within a specific repository.
        """
        search_result = await self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=top_k,
            query_filter=qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="repository_id",
                        match=qmodels.MatchValue(value=str(repository_id))
                    )
                ]
            )
        )
        
        # Add score into the payload or wrap in a response object.
        # For simplicity, we just inject score into the dictionary temporarily.
        # Better yet, return a tuple or dict if needed.
        results = []
        for scored_point in search_result.points:
            payload_data = scored_point.payload or {}
            # Add score for frontend usage
            payload_data["score"] = scored_point.score
            # We don't have score in the VectorPayload schema strictly, but we can pass it along
            results.append(payload_data)
            
        return results
