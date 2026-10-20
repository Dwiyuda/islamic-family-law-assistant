import pytest

from app.ingest.jsonl import write_chunks
from app.retrieval.fakes import HashEmbedder, OverlapReranker
from app.retrieval.index_manifest import corpus_hashes, write_manifest
from app.retrieval.indexer import build_index, open_retriever, rebuild, update_index
from app.retrieval.qdrant_store import QdrantStore


class CountingEmbedder(HashEmbedder):
    def __init__(self):
        super().__init__()
        self.texts = 0

    def encode(self, texts):
        self.texts += len(texts)
        return super().encode(texts)


def _index(tmp_path, chunks):
    write_chunks(tmp_path / "processed" / "chunks.jsonl", chunks)
    store = QdrantStore.local(tmp_path / "qdrant")
    build_index(chunks, HashEmbedder(), store)
    store.close()
    write_manifest(tmp_path / "qdrant", corpus_hashes(chunks), max_length=1024)


def test_build_index_in_batches(chunks):
    store = QdrantStore.memory()
    assert build_index(chunks, HashEmbedder(), store, batch_size=2) == 5
    store.close()


def test_build_index_with_pause(chunks):
    store = QdrantStore.memory()
    assert build_index(chunks, HashEmbedder(), store, batch_size=2, pause=0.0) == 5
    store.close()


def test_build_index_calls_cool_once_per_batch(chunks):
    store = QdrantStore.memory()
    calls = []
    build_index(chunks, HashEmbedder(), store, batch_size=2, cool=lambda: calls.append(1))
    store.close()
    assert len(calls) == 3


def test_open_retriever_round_trip(tmp_path, chunks):
    _index(tmp_path, chunks)
    retriever = open_retriever(tmp_path, tmp_path / "qdrant", HashEmbedder(), OverlapReranker())
    assert retriever.search("alasan perceraian taklik talak", top_k=1)[0].chunk_id == (
        "khi-1991:pasal-116")
    retriever.store.close()


def test_open_retriever_rejects_changed_text(tmp_path, chunks):
    _index(tmp_path, chunks)
    edited = [chunks[0].model_copy(update={"text": chunks[0].text + " tambahan"}), *chunks[1:]]
    write_chunks(tmp_path / "processed" / "chunks.jsonl", edited)
    with pytest.raises(RuntimeError, match="1 changed"):
        open_retriever(tmp_path, tmp_path / "qdrant", HashEmbedder())


def test_open_retriever_rejects_missing_manifest(tmp_path, chunks):
    write_chunks(tmp_path / "processed" / "chunks.jsonl", chunks)
    store = QdrantStore.local(tmp_path / "qdrant")
    build_index(chunks, HashEmbedder(), store)
    store.close()
    with pytest.raises(RuntimeError, match="manifest"):
        open_retriever(tmp_path, tmp_path / "qdrant", HashEmbedder())


def test_update_index_reembeds_only_changed(chunks):
    store = QdrantStore.memory()
    build_index(chunks, HashEmbedder(), store)
    edited = [chunks[0].model_copy(update={"text": "teks baru"}), *chunks[1:4]]
    emb = CountingEmbedder()
    n = update_index(edited, emb, store, changed=[chunks[0].chunk_id],
                     removed=[chunks[4].chunk_id], batch_size=2)
    assert n == 1 and emb.texts == 1 and store.count() == 4
    store.close()


def test_open_retriever_rejects_incomplete_index(tmp_path, chunks):
    write_chunks(tmp_path / "processed" / "chunks.jsonl", chunks)
    store = QdrantStore.local(tmp_path / "qdrant")
    build_index(chunks[:3], HashEmbedder(), store)
    store.close()
    write_manifest(tmp_path / "qdrant", corpus_hashes(chunks), max_length=1024)
    with pytest.raises(RuntimeError, match="incomplete"):
        open_retriever(tmp_path, tmp_path / "qdrant", HashEmbedder())
    QdrantStore.local(tmp_path / "qdrant").close()  # lock was released


class FailingEmbedder(HashEmbedder):
    def encode(self, texts):
        raise RuntimeError("thermal abort")


def test_aborted_rebuild_leaves_no_manifest(tmp_path, chunks):
    qdrant = tmp_path / "qdrant"
    write_manifest(qdrant, corpus_hashes(chunks), max_length=1024)
    store = QdrantStore.local(qdrant)
    with pytest.raises(RuntimeError, match="thermal"):
        rebuild(chunks, FailingEmbedder(), store, qdrant, 1024)
    store.close()
    assert not (qdrant / "index_manifest.json").exists()


def test_rebuild_writes_manifest_last(tmp_path, chunks):
    qdrant = tmp_path / "qdrant"
    store = QdrantStore.local(qdrant)
    assert rebuild(chunks, HashEmbedder(), store, qdrant, 1024, batch_size=2) == 5
    store.close()
    assert (qdrant / "index_manifest.json").exists()
