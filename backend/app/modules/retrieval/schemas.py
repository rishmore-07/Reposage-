"""
app/modules/retrieval/schemas.py

Retrieval API schemas.

Evolved from Phase 3D's RetrievedChunk to support multiple search modes
while maintaining backward compatibility.
"""

import uuid
from typing import Literal

from pydantic import BaseModel, Field


class SearchQueryRequest(BaseModel):
    """Request body for the search endpoint."""

    query: str = Field(..., min_length=1, max_length=1000)
    top_k: int = Field(default=10, ge=1, le=50)
    mode: Literal["semantic", "keyword", "hybrid"] = Field(
        default="hybrid",
        description="Retrieval strategy: semantic, keyword, or hybrid (RRF fusion).",
    )
    debug: bool = Field(
        default=False,
        description="Include detailed ranking information from each retrieval system.",
    )


class RetrievedChunk(BaseModel):
    """
    Legacy result schema from Phase 3D semantic search.

    Preserved for backward compatibility. New consumers should
    use SearchResult instead.
    """

    chunk_id: str
    repository_id: str
    indexed_file_id: str
    code_symbol_id: str | None = None
    file_path: str
    language: str
    chunk_type: str
    symbol_name: str | None = None
    start_line: int
    end_line: int
    content: str
    score: float


class SearchResult(BaseModel):
    """
    Unified search result supporting all retrieval modes.

    Superset of RetrievedChunk with additional fields for:
    - rank: position in the final result list
    - source: which retrieval system produced this result
    - debug fields: individual system rankings/scores (when debug=True)
    """

    chunk_id: str
    repository_id: str
    indexed_file_id: str | None = None
    code_symbol_id: str | None = None
    file_path: str
    language: str
    chunk_type: str
    symbol_name: str | None = None
    class_name: str | None = None
    parent_symbol: str | None = None
    module_name: str | None = None
    context_path: str | None = None
    start_line: int = 0
    end_line: int = 0
    content: str
    score: float
    rank: int = 0
    source: Literal["semantic", "keyword", "hybrid"] = "semantic"

    # Debug/evaluation fields — populated when debug=True
    semantic_rank: int | None = None
    keyword_rank: int | None = None
    semantic_score: float | None = None
    keyword_score: float | None = None
    rrf_score: float | None = None


class SearchQueryResponse(BaseModel):
    """Response from the search endpoint."""

    results: list[SearchResult]
    mode: str = "semantic"
    total_candidates: int = 0
