from app.retrieval.bm25 import BM25Index, tokenize
from app.retrieval.corpus import index_text


def test_tokenize_lowercases_and_drops_punctuation():
    assert tokenize("KHI Pasal 116: Talak (ba'in)!") == ["khi", "pasal", "116", "talak", "ba", "in"]
    # Harakat and Latin diacritics are dropped, otherwise \w splits voweled Arabic words.
    assert tokenize("قَالَ النبي raḍiyallāhu") == ["قال", "النبي", "radiyallahu"]


def test_index_text_prefixes_citation(chunks):
    assert index_text(chunks[0]).startswith("KHI Pasal 116\nPerceraian dapat")


def test_bm25_ranks_lexical_match_first(chunks):
    hits = BM25Index(chunks).search("alasan perceraian taklik talak", top_k=3)
    assert hits[0][0] == "khi-1991:pasal-116"
    assert len(hits) <= 3 and all(score > 0 for _, score in hits)


def test_bm25_allowed_filter(chunks):
    hits = BM25Index(chunks).search("perkawinan", top_k=5, allowed={"uu-7-1989:pasal-49"})
    assert [cid for cid, _ in hits] == ["uu-7-1989:pasal-49"]


def test_bm25_no_match_is_empty(chunks):
    assert BM25Index(chunks).search("zzzz qqqq", top_k=5) == []
