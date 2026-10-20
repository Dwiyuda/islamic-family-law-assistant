import math

import pytest

from app.evaluation.metrics import mrr_at_k, ndcg_at_k, recall_at_k


def test_recall_at_k():
    assert recall_at_k(["a", "x", "b"], {"a", "b"}, 2) == 0.5
    assert recall_at_k(["a", "x", "b"], {"a", "b"}, 3) == 1.0
    assert recall_at_k([], {"a"}, 5) == 0.0


def test_mrr_at_k():
    assert mrr_at_k(["x", "a"], {"a"}, 10) == 0.5
    assert mrr_at_k(["x", "y", "a"], {"a"}, 2) == 0.0


def test_ndcg_at_k():
    assert ndcg_at_k(["a", "b"], {"a", "b"}, 10) == pytest.approx(1.0)
    expected = (1 / math.log2(3)) / (1 / math.log2(2) + 1 / math.log2(3))
    assert ndcg_at_k(["x", "a"], {"a", "b"}, 10) == pytest.approx(expected)
    assert ndcg_at_k(["x"], {"a"}, 10) == 0.0
