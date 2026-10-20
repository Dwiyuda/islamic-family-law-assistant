import pytest
from pydantic import ValidationError

from app.ingest.jsonl import read_chunks, write_chunks
from app.ingest.models import Chunk, approx_tokens


def _reg(**over):
    data = {
        "chunk_id": "khi-1991:pasal-116",
        "doc_id": "khi-1991",
        "doc_title": "Kompilasi Hukum Islam",
        "source_type": "regulation",
        "domain": "perceraian",
        "hierarchy": {"buku": "I", "bab": "XVI", "bagian": None, "pasal": "116", "ayat": None},
        "citation": "KHI Pasal 116",
        "text": "Pasal 116\nPerceraian dapat terjadi karena alasan...",
        "source_url": "https://example.go.id/khi.pdf",
        "status": "berlaku",
        "license": "public-domain (UU 28/2014 Pasal 42)",
    }
    data.update(over)
    return Chunk(**data)


def test_roundtrip(tmp_path):
    path = tmp_path / "chunks.jsonl"
    assert write_chunks(path, [_reg()]) == 1
    [back] = read_chunks(path)
    assert back == _reg()
    assert back.visibility == "public"


def test_hadith_requires_meta():
    with pytest.raises(ValidationError):
        _reg(chunk_id="hadith:bukhari:6732", source_type="hadith", domain="kewarisan")


def test_non_hadith_rejects_meta():
    with pytest.raises(ValidationError):
        _reg(hadith={"kitab": "Sahih al-Bukhari", "nomor": "6732", "derajat": "sahih"})


def test_hadith_ok():
    c = _reg(
        chunk_id="hadith:bukhari:6732",
        source_type="hadith",
        domain="kewarisan",
        hadith={"kitab": "Sahih al-Bukhari", "nomor": "6732", "derajat": "sahih"},
        citation="HR. Bukhari no. 6732",
    )
    assert c.hadith.derajat == "sahih"


def test_bad_chunk_id():
    with pytest.raises(ValidationError):
        _reg(chunk_id="KHI Pasal 116")


def test_duplicate_ids_rejected(tmp_path):
    with pytest.raises(ValueError, match="duplicate chunk_id"):
        write_chunks(tmp_path / "x.jsonl", [_reg(), _reg()])


def test_approx_tokens():
    assert approx_tokens("a b c d") == 5
    assert approx_tokens("") == 0


def test_duplicate_ids_no_file_created(tmp_path):
    path = tmp_path / "chunks.jsonl"
    with pytest.raises(ValueError, match="duplicate chunk_id"):
        write_chunks(path, [_reg(), _reg()])
    assert not path.exists()


def test_duplicate_ids_preserves_existing_file(tmp_path):
    path = tmp_path / "chunks.jsonl"
    # Write a good file first
    write_chunks(path, [_reg()])
    original_content = path.read_text()
    # Try to overwrite with duplicates
    with pytest.raises(ValueError, match="duplicate chunk_id"):
        write_chunks(path, [_reg(), _reg()])
    # File must still exist and be unchanged
    assert path.exists()
    assert path.read_text() == original_content
