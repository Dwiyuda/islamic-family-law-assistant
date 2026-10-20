import json

import pytest

from app.ingest.build import build_private, build_public, stats

MANIFEST = """
sources:
  - {doc_id: khi-1991, judul: KHI, singkatan: KHI, jenis: inpres, url_sumber: "local", format: txt,
     lisensi: pd, domain: perkawinan, domain_rules: [{buku: "II", domain: kewarisan}]}
  - {doc_id: prosedur-cerai-gugat, judul: Prosedur, singkatan: Prosedur Cerai Gugat,
     jenis: prosedur, url_sumber: "local", format: txt, lisensi: resmi, domain: prosedur}
  - {doc_id: quran-ara, judul: QA, singkatan: QS, jenis: quran, url_sumber: "local", format: json,
     lisensi: la, domain: kewarisan}
  - {doc_id: quran-ind, judul: QI, singkatan: QS, jenis: quran, url_sumber: "local", format: json,
     lisensi: li, domain: kewarisan}
  - {doc_id: hadis-info, judul: HI, singkatan: HR, jenis: hadis, url_sumber: "local", format: json,
     lisensi: u, domain: kewarisan}
  - {doc_id: hadis-bukhari-ara, judul: BA, singkatan: HR, jenis: hadis, url_sumber: "local",
     format: json, lisensi: u, domain: kewarisan}
"""


@pytest.fixture
def data_dir(tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    (tmp_path / "sources.yaml").write_text(MANIFEST, encoding="utf-8")
    (raw / "khi-1991.txt").write_text(
        "BUKU I\nBAB I\nPasal 1\nIsi satu.\nBUKU II\nBAB I\nPasal 171\nIsi waris.\n",
        encoding="utf-8")
    (raw / "prosedur-cerai-gugat.txt").write_text("Langkah 1\nDaftar.", encoding="utf-8")
    verse = {"quran": [{"chapter": 4, "verse": 11, "text": "x"}]}
    (raw / "quran-ara.json").write_text(json.dumps(verse), encoding="utf-8")
    (raw / "quran-ind.json").write_text(json.dumps(verse), encoding="utf-8")
    info = {"bukhari": {"metadata": {"sections": {"85": "Laws of Inheritance"}},
                        "hadiths": [{"hadithnumber": 6732, "grades": [],
                                     "reference": {"book": 85, "hadith": 9}}]}}
    (raw / "hadis-info.json").write_text(json.dumps(info), encoding="utf-8")
    ed = {"hadiths": [{"hadithnumber": 6732, "text": "t", "reference": {"book": 85, "hadith": 9}}]}
    (raw / "hadis-bukhari-ara.json").write_text(json.dumps(ed), encoding="utf-8")
    return tmp_path


def test_build_public(data_dir):
    chunks = build_public(data_dir)
    ids = {c.chunk_id for c in chunks}
    assert ids == {"khi-1991:pasal-1", "khi-1991:pasal-171", "prosedur-cerai-gugat:bagian-1",
                   "quran:4:11", "hadith:bukhari:6732"}
    s = stats(chunks)
    assert s["total"] == 5
    assert s["by_source_type"] == {"regulation": 2, "procedure": 1, "quran": 1, "hadith": 1}
    assert s["by_domain"]["kewarisan"] == 3


def test_build_private_absent_is_empty(data_dir):
    assert build_private(data_dir) == []


def test_reference_sources_are_not_chunked(data_dir):
    manifest = data_dir / "sources.yaml"
    manifest.write_text(manifest.read_text(encoding="utf-8") + (
        "  - {doc_id: khi-ref, judul: KHI MA, singkatan: KHI, jenis: inpres, url_sumber: local,"
        " format: txt, lisensi: pd, domain: perkawinan, role: reference}\n"), encoding="utf-8")
    (data_dir / "raw" / "khi-ref.txt").write_text("BUKU I\nBAB I\nPasal 9\nIsi.\n",
                                                  encoding="utf-8")
    assert not [c for c in build_public(data_dir) if c.doc_id == "khi-ref"]


def test_build_private_book(data_dir):
    priv = data_dir / "private"
    (priv / "raw").mkdir(parents=True)
    (priv / "sources_private.yaml").write_text(
        "sources:\n  - {doc_id: buku-x, judul: Buku X, singkatan: Buku X, jenis: buku,"
        " url_sumber: local, format: txt, lisensi: hak cipta penulis, domain: kewarisan,"
        " visibility: private}\n", encoding="utf-8")
    (priv / "raw" / "buku-x.txt").write_text("Bab 1\nAshabul furudh.", encoding="utf-8")
    [chunk] = build_private(data_dir)
    assert chunk.visibility == "private" and chunk.source_type == "book"
