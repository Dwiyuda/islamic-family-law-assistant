import hashlib

import httpx
import pytest

from app.ingest.download import sync
from app.ingest.sources import load_sources

MANIFEST = """
sources:
  - doc_id: pp-9-1975
    judul: PP 9/1975
    singkatan: PP 9/1975
    jenis: pp
    url_sumber: https://peraturan.example.go.id/pp.txt
    format: txt
    lisensi: public-domain
    domain: perceraian
"""


def _client(body: bytes) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(lambda req: httpx.Response(200, content=body)))


def test_sync_downloads_and_records_hash(tmp_path):
    m = tmp_path / "sources.yaml"
    m.write_text(MANIFEST, encoding="utf-8")
    changed = sync(m, tmp_path / "raw", client=_client(b"Pasal 1\nisi"))
    assert changed == ["pp-9-1975"]
    [s] = load_sources(m)
    assert s.sha256 == hashlib.sha256(b"Pasal 1\nisi").hexdigest()
    assert s.tanggal_unduh is not None
    assert (tmp_path / "raw" / "pp-9-1975.txt").read_bytes() == b"Pasal 1\nisi"


def test_sync_skips_existing_and_detects_tampering(tmp_path):
    m = tmp_path / "sources.yaml"
    m.write_text(MANIFEST, encoding="utf-8")
    sync(m, tmp_path / "raw", client=_client(b"v1"))
    assert sync(m, tmp_path / "raw", client=_client(b"v2")) == []  # not re-downloaded
    (tmp_path / "raw" / "pp-9-1975.txt").write_bytes(b"edited")
    with pytest.raises(ValueError, match="sha256 mismatch"):
        sync(m, tmp_path / "raw", client=_client(b"v2"))


def test_sync_skips_non_http_fetchers(tmp_path):
    manifest = tmp_path / "sources.yaml"
    manifest.write_text(
        "sources:\n  - {doc_id: hadeethenc-id, judul: H, singkatan: H, jenis: hadis,"
        " url_sumber: 'https://hadeethenc.com/api/v1/', fetcher: hadeethenc, format: json,"
        " lisensi: t, domain: perkawinan}\n", encoding="utf-8")
    calls = []
    transport = httpx.MockTransport(lambda r: calls.append(r) or httpx.Response(200))
    with httpx.Client(transport=transport) as client:
        assert sync(manifest, tmp_path / "raw", client) == []
    assert calls == []
