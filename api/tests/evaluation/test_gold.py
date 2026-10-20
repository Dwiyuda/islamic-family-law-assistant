from collections import Counter

import pytest
from pydantic import ValidationError

from app.evaluation.gold import GOLD_PATH, GoldItem, load_gold
from app.retrieval.corpus import REPO_ROOT, load_corpus


def test_gold_item_rules():
    GoldItem(qid="cerai-001", question="Bagaimana cara cerai?", topic="perceraian",
             relevant_chunk_ids=["khi-1991:pasal-116"])
    with pytest.raises(ValidationError):
        GoldItem(qid="cerai-002", question="Bagaimana cara cerai?", topic="perceraian",
                 relevant_chunk_ids=[])
    with pytest.raises(ValidationError):
        GoldItem(qid="luar-001", question="Hukuman pencurian?", topic="luar_domain",
                 relevant_chunk_ids=["khi-1991:pasal-116"])
    with pytest.raises(ValidationError):
        GoldItem(qid="cerai-003", question="Bagaimana cara cerai?", topic="perceraian",
                 relevant_chunk_ids=["a", "b", "c", "d", "e", "f"])


def test_gold_file_composition_and_ids():
    gold = load_gold(GOLD_PATH)
    corpus_ids = {c.chunk_id for c in load_corpus(REPO_ROOT / "data")}
    assert len(gold) == 100 and len({g.qid for g in gold}) == 100
    topics = Counter(g.topic for g in gold)
    assert topics["luar_domain"] == 20
    assert topics["perceraian"] + topics["kewarisan"] + topics["peradilan"] == 80
    assert 30 <= topics["perceraian"] <= 40
    assert 25 <= topics["kewarisan"] <= 35
    assert 10 <= topics["peradilan"] <= 20
    missing = [(g.qid, cid) for g in gold for cid in g.relevant_chunk_ids if cid not in corpus_ids]
    assert missing == []
