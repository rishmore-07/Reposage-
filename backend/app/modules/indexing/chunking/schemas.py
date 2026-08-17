from typing import Optional
from pydantic import BaseModel
import uuid

class ChunkRequest(BaseModel):
    indexed_file_id: uuid.UUID
    code_symbol_id: uuid.UUID | None = None
    parent_chunk_id: uuid.UUID | None = None
    content: str
    chunk_type: str
    symbol_name: str | None = None
    language: str
    class_name: Optional[str] = None
    parent_symbol: Optional[str] = None
    module_name: Optional[str] = None
    context_path: Optional[str] = None
    
    start_line: int
    end_line: int
    start_byte: int | None = None
    end_byte: int | None = None
    content_hash: str
