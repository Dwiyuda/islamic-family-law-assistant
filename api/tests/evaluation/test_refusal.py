import json

import pytest

from app import config
from app.evaluation.refusal import choose_threshold
from app.retrieval.corpus import REPO_ROOT


def test_choose_threshold_separable_with_one_hard_case():
    choice = choose_threshold(in_scores=[0.9, 0.8, 0.7, 0.2], out_scores=[0.1, 0.3, 0.05])
    assert choice.threshold == pytest.approx(0.5)
    assert choice.refusal_accuracy == 1.0
    assert choice.false_refusal_rate == 0.25


def test_choose_threshold_prefers_lower_on_ties():
    # 0.35 and 0.8 both give balanced accuracy 0.75; the lower one refuses fewer real questions.
    choice = choose_threshold(in_scores=[0.6, 0.9], out_scores=[0.1, 0.7])
    assert choice.threshold == pytest.approx(0.35)
    assert choice.false_refusal_rate == 0.0


def test_config_matches_published_calibration():
    published = json.loads((REPO_ROOT / "eval" / "results" / "refusal.json")
                           .read_text(encoding="utf-8"))
    assert config.REFUSAL_THRESHOLD == pytest.approx(published["threshold"], abs=1e-4)
