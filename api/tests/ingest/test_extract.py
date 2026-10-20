import pytest

from app.ingest import extract
from app.ingest.extract import extract_text, normalize


def test_normalize_cleans_layout():
    raw = "Pasal 1\r\n  Perkawinan   ialah  ikatan\n12\n- 3 -\n\n\n\nPasal 2\n"
    assert normalize(raw) == "Pasal 1\nPerkawinan ialah ikatan\n\nPasal 2"


def test_normalize_joins_soft_hyphen():
    """Regression: 43 KHI chunks had U+00AD soft hyphens splitting words for BM25."""
    raw = "perka­\nwinan ke­dua"
    assert normalize(raw) == "perkawinan kedua"


def test_extract_txt(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("Pasal 1\n  isi  ", encoding="utf-8")
    assert extract_text(p) == "Pasal 1\nisi"


def test_extract_html_drops_scripts(tmp_path):
    p = tmp_path / "a.html"
    p.write_text(
        "<html><head><script>var x=1</script><style>p{}</style></head>"
        "<body><h1>Prosedur</h1><p>Langkah 1</p><nav>menu</nav></body></html>",
        encoding="utf-8",
    )
    text = extract_text(p)
    assert "Prosedur" in text and "Langkah 1" in text
    assert "var x" not in text and "menu" not in text


def test_extract_pdf_uses_pypdf(tmp_path, monkeypatch):
    class FakePage:
        def __init__(self, t):
            self._t = t

        def extract_text(self):
            return self._t

    class FakeReader:
        def __init__(self, path):
            self.pages = [FakePage("Pasal 1\nsatu"), FakePage("2\nPasal 2\ndua")]

    monkeypatch.setattr(extract, "PdfReader", FakeReader)
    p = tmp_path / "a.pdf"
    p.write_bytes(b"%PDF-fake")
    assert extract_text(p) == "Pasal 1\nsatu\nPasal 2\ndua"


def test_unsupported(tmp_path):
    p = tmp_path / "a.docx"
    p.write_bytes(b"x")
    with pytest.raises(ValueError):
        extract_text(p)
