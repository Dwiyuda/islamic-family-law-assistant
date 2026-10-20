import pytest

from app.ingest.sources import Source, load_sources, raw_path, save_sources

MANIFEST = """
sources:
  - doc_id: uu-1-1974
    judul: Undang-Undang Nomor 1 Tahun 1974 tentang Perkawinan
    singkatan: UU 1/1974
    jenis: uu
    nomor: "1"
    tahun: 1974
    status: diubah
    url_sumber: https://peraturan.example.go.id/uu-1-1974.pdf
    format: pdf
    lisensi: public-domain (UU 28/2014 Pasal 42)
    domain: perkawinan
    domain_rules:
      - bab: VIII
        domain: perceraian
      - bab: XIV
        domain: skip
"""


def test_load_and_resolve(tmp_path):
    p = tmp_path / "sources.yaml"
    p.write_text(MANIFEST, encoding="utf-8")
    [s] = load_sources(p)
    assert s.singkatan == "UU 1/1974"
    assert s.resolve_domain(None, "VIII") == "perceraian"
    assert s.resolve_domain(None, "XIV") == "skip"
    assert s.resolve_domain(None, "I") == "perkawinan"
    assert raw_path(s, tmp_path) == tmp_path / "uu-1-1974.pdf"


def test_duplicate_doc_id(tmp_path):
    p = tmp_path / "s.yaml"
    body = MANIFEST.split("sources:\n")[1]
    p.write_text("sources:\n" + body + body, encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate doc_id"):
        load_sources(p)


def test_private_source_in_public_manifest(tmp_path):
    p = tmp_path / "s.yaml"
    p.write_text(MANIFEST + "    visibility: private\n", encoding="utf-8")
    with pytest.raises(ValueError, match="visibility must be public"):
        load_sources(p)


def test_save_roundtrip(tmp_path):
    p = tmp_path / "s.yaml"
    p.write_text(MANIFEST, encoding="utf-8")
    sources = load_sources(p)
    sources[0].sha256 = "abc"
    save_sources(p, sources)
    assert load_sources(p)[0].sha256 == "abc"


def test_rule_needs_buku_and_bab_match():
    s = Source(
        doc_id="khi-1991", judul="KHI", singkatan="KHI", jenis="inpres",
        url_sumber="https://x.go.id/khi.pdf", format="pdf", lisensi="pd", domain="perkawinan",
        domain_rules=[{"buku": "II", "domain": "kewarisan"}, {"buku": "III", "domain": "skip"}],
    )
    assert s.resolve_domain("II", "III") == "kewarisan"
    assert s.resolve_domain("III", None) == "skip"
    assert s.resolve_domain("I", "XVI") == "perkawinan"


def test_manual_fetcher_and_new_fields_default():
    from app.ingest.sources import Source
    s = Source(doc_id="x", judul="X", singkatan="X", jenis="inpres", url_sumber="https://a.go.id",
               format="pdf", lisensi="pd", domain="perkawinan", fetcher="manual")
    assert s.text_replacements == {} and s.footnote_moves == {}
