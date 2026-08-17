"""
tests/unit/test_evaluation.py

Unit tests for retrieval evaluation metrics.
"""

import pytest
from app.modules.retrieval.evaluation import (
    recall_at_k,
    precision_at_k,
    mrr,
    compute_all_metrics,
    RetrievalMetrics,
)


class TestRecallAtK:
    def test_perfect_recall(self):
        retrieved = ["a", "b", "c"]
        relevant = ["a", "b", "c"]
        assert recall_at_k(retrieved, relevant, 3) == 1.0

    def test_partial_recall(self):
        retrieved = ["a", "b", "c", "d", "e"]
        relevant = ["a", "c", "f"]
        # Found: a, c → 2/3
        assert abs(recall_at_k(retrieved, relevant, 5) - 2 / 3) < 1e-9

    def test_zero_recall(self):
        retrieved = ["x", "y", "z"]
        relevant = ["a", "b"]
        assert recall_at_k(retrieved, relevant, 3) == 0.0

    def test_recall_k_smaller_than_retrieved(self):
        retrieved = ["a", "b", "c", "d"]
        relevant = ["a", "d"]
        # Only look at top 2: ["a", "b"] → found: a → 1/2
        assert recall_at_k(retrieved, relevant, 2) == 0.5

    def test_empty_relevant(self):
        assert recall_at_k(["a", "b"], [], 5) == 0.0

    def test_empty_retrieved(self):
        assert recall_at_k([], ["a", "b"], 5) == 0.0


class TestPrecisionAtK:
    def test_perfect_precision(self):
        retrieved = ["a", "b", "c"]
        relevant = ["a", "b", "c"]
        assert precision_at_k(retrieved, relevant, 3) == 1.0

    def test_partial_precision(self):
        retrieved = ["a", "x", "b", "y", "c"]
        relevant = ["a", "b", "c"]
        # top 5: 3 relevant out of 5 → 3/5
        assert abs(precision_at_k(retrieved, relevant, 5) - 0.6) < 1e-9

    def test_zero_precision(self):
        retrieved = ["x", "y", "z"]
        relevant = ["a", "b"]
        assert precision_at_k(retrieved, relevant, 3) == 0.0

    def test_k_zero(self):
        assert precision_at_k(["a"], ["a"], 0) == 0.0


class TestMRR:
    def test_first_result_relevant(self):
        retrieved = ["a", "b", "c"]
        relevant = ["a"]
        assert mrr(retrieved, relevant) == 1.0

    def test_second_result_relevant(self):
        retrieved = ["x", "a", "b"]
        relevant = ["a"]
        assert mrr(retrieved, relevant) == 0.5

    def test_third_result_relevant(self):
        retrieved = ["x", "y", "a"]
        relevant = ["a"]
        assert abs(mrr(retrieved, relevant) - 1 / 3) < 1e-9

    def test_no_relevant_found(self):
        retrieved = ["x", "y", "z"]
        relevant = ["a"]
        assert mrr(retrieved, relevant, max_k=3) == 0.0

    def test_multiple_relevant_first_counts(self):
        """MRR uses only the FIRST relevant result."""
        retrieved = ["x", "a", "b", "c"]
        relevant = ["a", "b", "c"]
        # First relevant is "a" at position 2 → 1/2
        assert mrr(retrieved, relevant) == 0.5

    def test_empty_lists(self):
        assert mrr([], ["a"]) == 0.0
        assert mrr(["a"], []) == 0.0


class TestComputeAllMetrics:
    def test_all_metrics_computed(self):
        retrieved = ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"]
        relevant = ["a", "c", "f"]

        metrics = compute_all_metrics(retrieved, relevant)

        assert isinstance(metrics, RetrievalMetrics)
        # Recall@5: found a, c in top 5 → 2/3
        assert abs(metrics.recall_at_5 - 2 / 3) < 1e-9
        # Recall@10: found a, c, f in top 10 → 3/3 = 1.0
        assert metrics.recall_at_10 == 1.0
        # Precision@5: 2 relevant in top 5 → 2/5
        assert abs(metrics.precision_at_5 - 0.4) < 1e-9
        # Precision@10: 3 relevant in top 10 → 3/10
        assert abs(metrics.precision_at_10 - 0.3) < 1e-9
        # MRR@10: first relevant at position 1 → 1.0
        assert metrics.mrr_at_10 == 1.0

    def test_no_results(self):
        metrics = compute_all_metrics([], ["a", "b"])
        assert metrics.recall_at_5 == 0.0
        assert metrics.recall_at_10 == 0.0
        assert metrics.precision_at_5 == 0.0
        assert metrics.precision_at_10 == 0.0
        assert metrics.mrr_at_10 == 0.0
