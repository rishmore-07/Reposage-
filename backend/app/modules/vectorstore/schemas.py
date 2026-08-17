import uuid
from pydantic import BaseModel

class VectorPayload(BaseModel):
    chunk_id: str
    repository_id: str
    indexed_file_id: str
    code_symbol_id: str | None = None
    file_path: str
    language: str
    chunk_type: str
    symbol_name: str | None = None
    class_name: str | None = None
    parent_symbol: str | None = None
    module_name: str | None = None
    context_path: str | None = None
    start_line: int
    end_line: int
    content: str
