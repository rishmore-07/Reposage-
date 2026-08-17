"""
tests/unit/test_rrf.py

Unit tests for Reciprocal Rank Fusion (RRF) implementation.
"""

import pytest
from app.modules.retrieval.rrf import reciprocal_rank_fusion, FusedResult


def _make_result(chunk_id, score=0.5, **kwargs):
    """Helper to create a minimal result dict."""
    return {
        "chunk_id": chunk_id,
        "repository_id": "repo-1",
        "file_path": f"path/to/{chunk_id}.py",
        "language": "python",
        "chunk_type": "function",
        "symbol_name": chunk_id,
        "content": f"def {chunk_id}(): pass",
        "score": score,
        "start_line": 1,
        "end_line": 5,
        **kwargs,
    }


class TestRRFCalculation:
    """Tests for RRF score computation correctness."""

    def test_rrf_basic_formula(self):
        """Verify RRF scores match the formula: 1/(k+rank)."""
        k = 60
        semantic = [_make_result("A", score=0.9)]
        keyword = [_make_result("B", score=5.0)]

        fused = reciprocal_rank_fusion(semantic, keyword, k=k)

        a_result = next(r for r in fused if r.chunk_id == "A")
        b_result = next(r for r in fused if r.chunk_id == "B")

        # A: only in semantic at rank 1 → 1/(60+1)
        assert abs(a_result.rrf_score - 1.0 / (k + 1)) < 1e-9

        # B: only in keyword at rank 1 → 1/(60+1)
        assert abs(b_result.rrf_score - 1.0 / (k + 1)) < 1e-9

    def test_rrf_combined_scores(self):
        """A chunk appearing in both lists gets contributions from both."""
        k = 60
        semantic = [_make_result("A"), _make_result("B")]
        keyword = [_make_result("B"), _make_result("A")]

        fused = reciprocal_rank_fusion(semantic, keyword, k=k)

        a_result = next(r for r in fused if r.chunk_id == "A")
        b_result = next(r for r in fused if r.chunk_id == "B")

        # A: semantic rank 1 + keyword rank 2 → 1/(61) + 1/(62)
        expected_a = 1.0 / (k + 1) + 1.0 / (k + 2)
        assert abs(a_result.rrf_score - expected_a) < 1e-9

        # B: semantic rank 2 + keyword rank 1 → 1/(62) + 1/(61)
        expected_b = 1.0 / (k + 2) + 1.0 / (k + 1)
        assert abs(b_result.rrf_score - expected_b) < 1e-9

        # A and B should have equal scores in this symmetric case
        assert abs(a_result.rrf_score - b_result.rrf_score) < 1e-9

    def test_rrf_ordering_favors_higher_ranks(self):
        """Document appearing at rank 1 in both systems should rank highest."""
        k = 60
        semantic = [_make_result("A"), _make_result("B"), _make_result("C")]
        keyword = [_make_result("A"), _make_result("C"), _make_result("B")]

        fused = reciprocal_rank_fusion(semantic, keyword, k=k)

        # A appears at rank 1 in both → highest fused score
        assert fused[0].chunk_id == "A"

    def test_rrf_custom_k(self):
        """RRF with different k values."""
        semantic = [_make_result("A")]
        keyword = []

        # k=1: score = 1/(1+1) = 0.5
        fused_k1 = reciprocal_rank_fusion(semantic, keyword, k=1)
        assert abs(fused_k1[0].rrf_score - 0.5) < 1e-9

        # k=0: score = 1/(0+1) = 1.0
        fused_k0 = reciprocal_rank_fusion(semantic, keyword, k=0)
        assert abs(fused_k0[0].rrf_score - 1.0) < 1e-9


class TestRRFDeduplication:
    """Tests for chunk deduplication during fusion."""

    def test_duplicate_chunks_merged(self):
        """Same chunk_id in both lists should produce only one result."""
        semantic = [_make_result("A")]
        keyword = [_make_result("A")]

        fused = reciprocal_rank_fusion(semantic, keyword, k=60)

        assert len(fused) == 1
        assert fused[0].chunk_id == "A"

    def test_duplicate_preserves_both_ranks(self):
        """Merged result should have both semantic and keyword ranks."""
        semantic = [_make_result("X", score=0.8), _make_result("Y", score=0.5)]
        keyword = [_make_result("Y", score=3.0), _make_result("X", score=1.0)]

        fused = reciprocal_rank_fusion(semantic, keyword, k=60)

        x_result = next(r for r in fused if r.chunk_id == "X")
        y_result = next(r for r in fused if r.chunk_id == "Y")

        assert x_result.semantic_rank == 1
        assert x_result.keyword_rank == 2
        assert x_result.semantic_score == 0.8
        assert x_result.keyword_score == 1.0

        assert y_result.semantic_rank == 2
        assert y_result.keyword_rank == 1
        assert y_result.semantic_score == 0.5
        assert y_result.keyword_score == 3.0


class TestRRFEdgeCases:
    """Tests for edge cases."""

    def test_empty_both_lists(self):
        """Both lists empty should return empty."""
        fused = reciprocal_rank_fusion([], [], k=60)
        assert fused == []

    def test_empty_semantic_list(self):
        """Only keyword results should still produce output."""
        keyword = [_make_result("A"), _make_result("B")]
        fused = reciprocal_rank_fusion([], keyword, k=60)

        assert len(fused) == 2
        for r in fused:
            assert r.semantic_rank is None
            assert r.keyword_rank is not None

    def test_empty_keyword_list(self):
        """Only semantic results should still produce output."""
        semantic = [_make_result("A"), _make_result("B")]
        fused = reciprocal_rank_fusion(semantic, [], k=60)

        assert len(fused) == 2
        for r in fused:
            assert r.semantic_rank is not None
            assert r.keyword_rank is None

    def test_single_result_each(self):
        """One result per list, different chunks."""
        semantic = [_make_result("A")]
        keyword = [_make_result("B")]

        fused = reciprocal_rank_fusion(semantic, keyword, k=60)
        assert len(fused) == 2

    def test_fused_ranks_are_sequential(self):
        """Fused ranks should be 1, 2, 3, ..."""
        semantic = [_make_result("A"), _make_result("B"), _make_result("C")]
        keyword = [_make_result("D"), _make_result("E")]

        fused = reciprocal_rank_fusion(semantic, keyword, k=60)
        ranks = [r.fused_rank for r in fused]
        assert ranks == list(range(1, len(fused) + 1))

    def test_result_metadata_preserved(self):
        """File path, language, and other metadata should be preserved."""
        semantic = [_make_result("A", file_path="src/auth.py", language="python")]
        fused = reciprocal_rank_fusion(semantic, [], k=60)

        assert fused[0].file_path == "src/auth.py"
        assert fused[0].language == "python"
