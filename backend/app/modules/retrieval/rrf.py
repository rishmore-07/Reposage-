"""
app/modules/retrieval/rrf.py

Reciprocal Rank Fusion (RRF) for combining ranked result lists.

RRF avoids the problem of directly summing scores from different systems
(e.g. BM25 scores vs cosine similarity) which have incompatible distributions.

Formula:
    RRF_score(d) = Σ 1 / (k + rank_i(d))

where k is a constant (default 60) and rank_i(d) is the rank of document d
in the i-th ranked list (1-indexed).

Reference:
    Cormack, Clarke, Büttcher (2009) — "Reciprocal Rank Fusion outperforms
    Condorcet and individual Rank Learning Methods"
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FusedResult:
    """
    A single search result after RRF fusion.

    Preserves original rankings and scores from each retrieval system
    for debugging and evaluation purposes.
    """

    chunk_id: str
    repository_id: str
    file_path: str
    language: str
    chunk_type: str
    symbol_name: str | None
    content: str

    # RRF output
    rrf_score: float = 0.0
    fused_rank: int = 0

    # Provenance from individual retrieval systems
    semantic_rank: int | None = None
    keyword_rank: int | None = None
    semantic_score: float | None = None
    keyword_score: float | None = None

    # Additional metadata carried through from retrieval
    indexed_file_id: str | None = None
    code_symbol_id: str | None = None
    start_line: int = 0
    end_line: int = 0


def reciprocal_rank_fusion(
    semantic_results: list[dict],
    keyword_results: list[dict],
    k: int = 60,
) -> list[FusedResult]:
    """
    Combine two ranked result lists using Reciprocal Rank Fusion.

    Each result dict must contain at minimum:
        - chunk_id: str (stable identity for deduplication)
        - repository_id, file_path, language, chunk_type, content
        - score: float (original retrieval score)

    Args:
        semantic_results: Ranked results from semantic/vector search (best first).
        keyword_results: Ranked results from keyword/BM25 search (best first).
        k: RRF constant. Higher values reduce the impact of high-ranked items.
            Default is 60 (standard value from the literature).

    Returns:
        Deduplicated list of FusedResult, sorted by descending RRF score.
    """
    # Build lookup: chunk_id -> FusedResult
    fused: dict[str, FusedResult] = {}

    # Process semantic results (1-indexed ranks)
    for rank_idx, result in enumerate(semantic_results, start=1):
        chunk_id = result["chunk_id"]
        rrf_contribution = 1.0 / (k + rank_idx)

        if chunk_id not in fused:
            fused[chunk_id] = FusedResult(
                chunk_id=chunk_id,
                repository_id=result.get("repository_id", ""),
                file_path=result.get("file_path", ""),
                language=result.get("language", ""),
                chunk_type=result.get("chunk_type", ""),
                symbol_name=result.get("symbol_name"),
                content=result.get("content", ""),
                indexed_file_id=result.get("indexed_file_id"),
                code_symbol_id=result.get("code_symbol_id"),
                start_line=result.get("start_line", 0),
                end_line=result.get("end_line", 0),
            )

        fused[chunk_id].rrf_score += rrf_contribution
        fused[chunk_id].semantic_rank = rank_idx
        fused[chunk_id].semantic_score = result.get("score")

    # Process keyword results (1-indexed ranks)
    for rank_idx, result in enumerate(keyword_results, start=1):
        chunk_id = result["chunk_id"]
        rrf_contribution = 1.0 / (k + rank_idx)

        if chunk_id not in fused:
            fused[chunk_id] = FusedResult(
                chunk_id=chunk_id,
                repository_id=result.get("repository_id", ""),
                file_path=result.get("file_path", ""),
                language=result.get("language", ""),
                chunk_type=result.get("chunk_type", ""),
                symbol_name=result.get("symbol_name"),
                content=result.get("content", ""),
                indexed_file_id=result.get("indexed_file_id"),
                code_symbol_id=result.get("code_symbol_id"),
                start_line=result.get("start_line", 0),
                end_line=result.get("end_line", 0),
            )

        fused[chunk_id].rrf_score += rrf_contribution
        fused[chunk_id].keyword_rank = rank_idx
        fused[chunk_id].keyword_score = result.get("score")

    # Sort by descending RRF score
    sorted_results = sorted(fused.values(), key=lambda r: r.rrf_score, reverse=True)

    # Assign final fused ranks (1-indexed)
    for i, result in enumerate(sorted_results, start=1):
        result.fused_rank = i

    return sorted_results
