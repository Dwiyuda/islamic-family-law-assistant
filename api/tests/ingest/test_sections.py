from app.ingest.models import approx_tokens
from app.ingest.sections import chunk_sections
from app.ingest.sources import Source


def _src(**over):
    data = {
        "doc_id": "prosedur-cerai-gugat",
        "judul": "Prosedur Cerai Gugat",
        "singkatan": "Prosedur Cerai Gugat",
        "jenis": "prosedur",
        "url_sumber": "https://pa-x.go.id/p.html",
        "format": "html",
        "lisensi": "dokumen resmi",
        "domain": "prosedur",
    }
    data.update(over)
    return Source(**data)


def test_packs_small_paragraphs():
    text = "Langkah 1\nDaftar ke meja PTSP.\n\nLangkah 2\nBayar panjar.\n\nLangkah 3\nSidang."
    [chunk] = chunk_sections(text, _src(), "procedure")
    assert chunk.chunk_id == "prosedur-cerai-gugat:bagian-1"
    assert chunk.citation == "Prosedur Cerai Gugat, bagian 1"
    assert chunk.source_type == "procedure" and chunk.domain == "prosedur"
    assert "Langkah 3" in chunk.text


def test_respects_max_tokens():
    para = " ".join(["kata"] * 150)  # ~195 tokens each
    text = "\n\n".join([para] * 5)
    chunks = chunk_sections(text, _src(), "procedure")
    assert len(chunks) == 5
    assert all(approx_tokens(c.text) <= 350 for c in chunks)


def test_oversized_paragraph_split_by_sentence():
    sentence = " ".join(["kata"] * 60) + "."
    text = " ".join([sentence] * 8)  # one paragraph ~630 tokens
    chunks = chunk_sections(text, _src(), "procedure")
    assert len(chunks) >= 2
    assert all(approx_tokens(c.text) <= 350 for c in chunks)


def test_private_book_keeps_visibility():
    s = _src(doc_id="buku-faraid-x", jenis="buku", singkatan="Buku X", domain="kewarisan",
             visibility="private", url_sumber="local:data/private/raw/buku-faraid-x.pdf")
    [chunk] = chunk_sections("Bab 1\nAshabul furudh.", s, "book")
    assert chunk.visibility == "private" and chunk.source_type == "book"


from app.ingest.sections import chunk_procedure_html

STEPS_HTML = """<html><body><div class="item-page"><h3>Cerai Gugat</h3>
<dl><dd>Hits: 42770</dd></dl>
<ol><li><strong>Langkah pertama:</strong><ul><li>Mengajukan gugatan.</li></ul></li>
<li><strong>Membayar biaya perkara</strong><p>-</p></li></ol></div>
<div class="footer">Userway</div></body></html>"""

LISTS_HTML = """<div class="entry-content"><p>SYARAT PENGAJUAN</p>
<ol><li>Fotokopi KTP</li><li>Membayar panjar</li></ol>
<p>Catatan :</p><ul><li>Bawa asli.</li></ul></div>"""


def _proc(**overrides):
    fields = {
        "doc_id": "prosedur-x", "judul": "Prosedur X", "singkatan": "Prosedur X",
        "jenis": "prosedur", "url_sumber": "https://pa.example.go.id/x", "format": "html",
        "lisensi": "resmi", "domain": "prosedur",
    }
    return Source(**{**fields, **overrides})


def test_procedure_steps():
    chunks = chunk_procedure_html(STEPS_HTML, _proc(html_selector="div.item-page"))
    assert [c.chunk_id for c in chunks] == ["prosedur-x:langkah-1", "prosedur-x:langkah-2"]
    assert [c.citation for c in chunks] == ["Prosedur X langkah 1", "Prosedur X langkah 2"]
    assert chunks[0].text == "Langkah pertama:\nMengajukan gugatan."
    assert chunks[1].text == "Membayar biaya perkara"
    assert all(c.source_type == "procedure" for c in chunks)


def test_procedure_lists_keep_their_heading():
    src = _proc(html_selector="div.entry-content", procedure_unit="list")
    chunks = chunk_procedure_html(LISTS_HTML, src)
    assert [c.chunk_id for c in chunks] == ["prosedur-x:bagian-1", "prosedur-x:bagian-2"]
    assert chunks[0].text == "SYARAT PENGAJUAN\nFotokopi KTP\nMembayar panjar"
    assert chunks[1].text == "Catatan :\nBawa asli."


def test_procedure_selector_must_match():
    import pytest
    with pytest.raises(ValueError):
        chunk_procedure_html(LISTS_HTML, _proc(html_selector="div.missing"))
