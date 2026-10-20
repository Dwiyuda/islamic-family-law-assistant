import pytest

from app.ingest.models import Chunk


def _chunk(chunk_id: str, domain: str, citation: str, text: str) -> Chunk:
    return Chunk(chunk_id=chunk_id, doc_id=chunk_id.split(":")[0], doc_title="Doc",
                 source_type="regulation", domain=domain, citation=citation, text=text,
                 source_url="https://peraturan.example.go.id", license="public-domain")


@pytest.fixture
def chunks() -> list[Chunk]:
    return [
        _chunk("khi-1991:pasal-116", "perceraian", "KHI Pasal 116",
               "Perceraian dapat terjadi karena alasan suami melanggar taklik talak atau "
               "pertengkaran terus menerus."),
        _chunk("khi-1991:pasal-176", "kewarisan", "KHI Pasal 176",
               "Anak perempuan bila hanya seorang ia mendapat separoh bagian."),
        _chunk("uu-1-1974:pasal-7", "perkawinan", "UU 1/1974 Pasal 7",
               "Perkawinan hanya diizinkan bila pria dan wanita sudah mencapai umur 19 tahun."),
        _chunk("uu-7-1989:pasal-49", "peradilan", "UU 7/1989 Pasal 49",
               "Pengadilan agama bertugas memeriksa perkara perkawinan, waris, wasiat, hibah."),
        _chunk("khi-1991:pasal-149", "perceraian", "KHI Pasal 149",
               "Bilamana perkawinan putus karena talak, bekas suami wajib memberikan mut'ah "
               "dan nafkah iddah."),
    ]


@pytest.fixture
def retriever(chunks):
    from app.retrieval.bm25 import BM25Index
    from app.retrieval.corpus import index_text
    from app.retrieval.fakes import HashEmbedder, OverlapReranker
    from app.retrieval.qdrant_store import QdrantStore
    from app.retrieval.retriever import Retriever

    emb = HashEmbedder()
    store = QdrantStore.memory()
    store.recreate(emb.dim)
    store.upsert(chunks, emb.encode([index_text(c) for c in chunks]))
    yield Retriever(chunks, BM25Index(chunks), store, emb, OverlapReranker())
    store.close()
