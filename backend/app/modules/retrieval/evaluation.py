"""
app/modules/retrieval/evaluation.py

Retrieval quality metrics for comparing search strategies.

Implements:
- Recall@K
- Precision@K
- Mean Reciprocal Rank (MRR)

These are standard Information Retrieval metrics used to measure
how well a search system retrieves relevant documents.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RetrievalMetrics:
    """Container for computed retrieval metrics."""

    recall_at_5: float = 0.0
    recall_at_10: float = 0.0
    precision_at_5: float = 0.0
    precision_at_10: float = 0.0
    mrr_at_10: float = 0.0


def recall_at_k(retrieved_ids: list[str], relevant_ids: list[str], k: int) -> float:
    """
    Recall@K: fraction of relevant items found in the top-K retrieved results.

    recall@K = |relevant ∩ retrieved[:k]| / |relevant|

    Args:
        retrieved_ids: Ordered list of chunk IDs from the search system.
        relevant_ids: Ground-truth list of relevant chunk IDs.
        k: Number of top results to consider.

    Returns:
        Recall score between 0.0 and 1.0. Returns 0.0 if relevant_ids is empty.
    """
    if not relevant_ids:
        return 0.0

    relevant_set = set(relevant_ids)
    retrieved_top_k = set(retrieved_ids[:k])
    found = relevant_set & retrieved_top_k

    return len(found) / len(relevant_set)


def precision_at_k(retrieved_ids: list[str], relevant_ids: list[str], k: int) -> float:
    """
    Precision@K: fraction of top-K retrieved results that are relevant.

    precision@K = |relevant ∩ retrieved[:k]| / k

    Args:
        retrieved_ids: Ordered list of chunk IDs from the search system.
        relevant_ids: Ground-truth list of relevant chunk IDs.
        k: Number of top results to consider.

    Returns:
        Precision score between 0.0 and 1.0. Returns 0.0 if k is 0.
    """
    if k == 0:
        return 0.0

    relevant_set = set(relevant_ids)
    retrieved_top_k = set(retrieved_ids[:k])
    found = relevant_set & retrieved_top_k

    return len(found) / k


def mrr(retrieved_ids: list[str], relevant_ids: list[str], max_k: int = 10) -> float:
    """
    Mean Reciprocal Rank: 1 / rank of the first relevant result.

    MRR = 1 / rank_of_first_relevant_in_top_k

    Args:
        retrieved_ids: Ordered list of chunk IDs from the search system.
        relevant_ids: Ground-truth list of relevant chunk IDs.
        max_k: Maximum rank position to consider.

    Returns:
        MRR score between 0.0 and 1.0. Returns 0.0 if no relevant item found in top-K.
    """
    relevant_set = set(relevant_ids)

    for i, chunk_id in enumerate(retrieved_ids[:max_k]):
        if chunk_id in relevant_set:
            return 1.0 / (i + 1)

    return 0.0


def compute_all_metrics(
    retrieved_ids: list[str],
    relevant_ids: list[str],
) -> RetrievalMetrics:
    """
    Compute all standard retrieval metrics.

    Args:
        retrieved_ids: Ordered list of chunk IDs from the search system.
        relevant_ids: Ground-truth list of relevant chunk IDs.

    Returns:
        RetrievalMetrics with Recall@5, Recall@10, Precision@5, Precision@10, MRR@10.
    """
    return RetrievalMetrics(
        recall_at_5=recall_at_k(retrieved_ids, relevant_ids, 5),
        recall_at_10=recall_at_k(retrieved_ids, relevant_ids, 10),
        precision_at_5=precision_at_k(retrieved_ids, relevant_ids, 5),
        precision_at_10=precision_at_k(retrieved_ids, relevant_ids, 10),
        mrr_at_10=mrr(retrieved_ids, relevant_ids, 10),
    )
