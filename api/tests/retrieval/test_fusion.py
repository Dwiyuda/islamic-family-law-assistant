import pytest

from app.retrieval.fusion import rrf


def test_rrf_orders_by_summed_reciprocal_rank():
    fused = rrf([["a", "b", "c"], ["b", "a"], ["b"]], k=60)
    assert [cid for cid, _ in fused] == ["b", "a", "c"]
    assert fused[0][1] == pytest.approx(1 / 62 + 1 / 61 + 1 / 61)
    assert fused[2][1] == pytest.approx(1 / 63)


def test_rrf_ties_break_by_id_and_empty_input():
    assert [cid for cid, _ in rrf([["y"], ["x"]])] == ["x", "y"]
    assert rrf([]) == []
