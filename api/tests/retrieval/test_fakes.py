import math

from app.retrieval.fakes import HashEmbedder, OverlapReranker


def test_hash_embedder_is_deterministic_and_normalized():
    emb = HashEmbedder()
    a, b = emb.encode(["Talak raj'i", "Talak raj'i"])
    assert a == b
    assert math.isclose(sum(x * x for x in a.dense), 1.0)
    assert len(a.dense) == emb.dim and a.sparse


def test_hash_embedder_similarity_follows_word_overlap():
    emb = HashEmbedder()
    q, near, far = emb.encode(["nafkah iddah talak", "nafkah iddah setelah talak",
                               "zakat fitrah beras"])
    dot = lambda x, y: sum(i * j for i, j in zip(x.dense, y.dense))
    assert dot(q, near) > dot(q, far)


def test_hash_embedder_empty_text_has_nonempty_sparse():
    [e] = HashEmbedder().encode([""])
    assert e.sparse == {0: 0.0}


def test_overlap_reranker():
    scores = OverlapReranker().score("nafkah iddah", ["nafkah iddah wajib", "iddah", "zakat"])
    assert scores == [1.0, 0.5, 0.0]
    assert OverlapReranker().score("x", []) == []
