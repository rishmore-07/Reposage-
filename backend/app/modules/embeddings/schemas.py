import uuid
from typing import Literal
from pydantic import BaseModel

class EmbeddingConfig(BaseModel):
    provider: Literal["ollama", "gemini"]
    model: str
    dimension: int
    base_url: str | None = None
    api_key: str | None = None
