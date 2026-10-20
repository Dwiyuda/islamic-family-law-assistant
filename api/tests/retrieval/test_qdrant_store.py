import pytest

from app.retrieval.corpus import index_text
from app.retrieval.fakes import HashEmbedder
from app.retrieval.qdrant_store import QdrantStore, point_id


@pytest.fixture
def store(chunks):
    emb = HashEmbedder()
    s = QdrantStore.memory()
    s.recreate(emb.dim)
    s.upsert(chunks, emb.encode([index_text(c) for c in chunks]))
    yield s
    s.close()


def test_point_id_is_stable():
    assert point_id("khi-1991:pasal-116") == point_id("khi-1991:pasal-116")
    assert point_id("khi-1991:pasal-116") != point_id("khi-1991:pasal-117")


@pytest.mark.parametrize("using", ["dense", "sparse"])
def test_search_finds_obvious_chunk(store, using):
    [q] = HashEmbedder().encode(["alasan perceraian taklik talak"])
    hits = store.search(using, q, top_k=2)
    assert hits[0][0] == "khi-1991:pasal-116" and len(hits) == 2


def test_domain_filter(store):
    [q] = HashEmbedder().encode(["bagian anak perempuan"])
    hits = store.search("dense", q, top_k=5, domains={"kewarisan"})
    assert [cid for cid, _ in hits] == ["khi-1991:pasal-176"]


def test_count_and_recreate(store):
    assert store.count() == 5
    store.recreate(HashEmbedder().dim)
    assert store.count() == 0


def test_count_without_collection():
    assert QdrantStore.memory().count() == 0


def test_delete_and_has_all(store, chunks):
    ids = [c.chunk_id for c in chunks]
    assert store.has_all(ids)
    store.delete([ids[0]])
    assert store.count() == 4
    assert not store.has_all(ids)
    assert store.has_all(ids[1:])
    store.delete([])  # no-op
    assert store.count() == 4
