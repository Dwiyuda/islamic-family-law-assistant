from collections import Counter

from app.evaluation.gold import GOLD_PATH, load_gold
from app.retrieval.corpus import REPO_ROOT, load_corpus

HELDOUT = REPO_ROOT / "eval" / "heldout.jsonl"


def _norm(text: str) -> str:
    return " ".join(text.lower().split())


def test_heldout_set_is_valid_and_separate_from_gold():
    gold, held = load_gold(GOLD_PATH), load_gold(HELDOUT)
    assert Counter(h.topic for h in held) == {"perceraian": 8, "kewarisan": 8,
                                              "peradilan": 4, "luar_domain": 20}
    qids = [h.qid for h in held]
    assert len(set(qids)) == 40 and set(qids).isdisjoint(g.qid for g in gold)
    assert {_norm(h.question) for h in held}.isdisjoint(_norm(g.question) for g in gold)
    corpus_ids = {c.chunk_id for c in load_corpus(REPO_ROOT / "data")}
    assert all(set(h.relevant_chunk_ids) <= corpus_ids for h in held)
