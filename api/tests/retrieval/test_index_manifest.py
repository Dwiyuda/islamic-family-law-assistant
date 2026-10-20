from app.retrieval.index_manifest import (
    corpus_hashes,
    diff,
    read_manifest,
    text_hash,
    write_manifest,
)


def test_text_hash_follows_index_text(chunks):
    a = chunks[0]
    assert text_hash(a) == text_hash(a.model_copy())
    assert text_hash(a) != text_hash(a.model_copy(update={"text": a.text + " x"}))


def test_manifest_round_trip_and_diff(tmp_path, chunks):
    hashes = corpus_hashes(chunks)
    assert read_manifest(tmp_path) is None
    write_manifest(tmp_path, hashes, max_length=1024)
    manifest = read_manifest(tmp_path)
    assert manifest["model"] == "BAAI/bge-m3" and manifest["max_length"] == 1024
    assert diff(manifest, hashes) == ([], [])
    changed = {**hashes, chunks[0].chunk_id: "x", "new:1": "y"}
    del changed[chunks[1].chunk_id]
    assert diff(manifest, changed) == (sorted([chunks[0].chunk_id, "new:1"]),
                                       [chunks[1].chunk_id])
