import pytest

from app.retrieval.retriever import METHODS, Retriever


@pytest.mark.parametrize("method", METHODS)
def test_every_method_finds_the_obvious_chunk(retriever, method):
    hits = retriever.search("alasan perceraian taklik talak", top_k=3, method=method)
    assert hits[0].chunk_id == "khi-1991:pasal-116" and len(hits) <= 3


@pytest.mark.parametrize("method", METHODS)
def test_domain_filter_applies_to_every_method(retriever, method):
    hits = retriever.search("bagian anak perempuan talak", top_k=5, method=method,
                            domains={"kewarisan"})
    assert hits and {h.chunk_id for h in hits} == {"khi-1991:pasal-176"}


def test_rerank_score_only_for_hybrid_rerank(retriever):
    assert retriever.search("talak", method="hybrid_rerank")[0].rerank_score is not None
    assert retriever.search("talak", method="hybrid")[0].rerank_score is None


def test_unknown_method_and_missing_reranker(chunks, retriever):
    with pytest.raises(ValueError):
        retriever.search("talak", method="magic")
    bare = Retriever(chunks, retriever.bm25, retriever.store, retriever.embedder)
    with pytest.raises(ValueError):
        bare.search("talak", method="hybrid_rerank")
