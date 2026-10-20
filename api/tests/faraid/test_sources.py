from app.faraid.sources import DASAR, dasar
from app.retrieval.corpus import REPO_ROOT, load_corpus


def test_every_dasar_chunk_exists_in_corpus():
    corpus_ids = {c.chunk_id for c in load_corpus(REPO_ROOT / "data")}
    for nama, ids in DASAR.items():
        for cid in ids:
            assert cid in corpus_ids, f"{nama}: {cid} tidak ada di korpus"


def test_dasar_lookup():
    assert "khi-1991:pasal-176" in dasar("anak_perempuan")
    assert "khi-1991:pasal-193" in dasar("radd")
    assert dasar("tidak_ada") == []
