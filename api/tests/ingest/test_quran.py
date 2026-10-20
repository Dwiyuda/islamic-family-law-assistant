from app.ingest.quran import QURAN_SELECTION, clean_translation, parse_quran
from app.ingest.sources import Source


def _src(doc_id):
    return Source(doc_id=doc_id, judul=doc_id, singkatan="QS", jenis="quran",
                  url_sumber=f"https://cdn.example/{doc_id}.json", format="json",
                  lisensi=f"lic-{doc_id}", domain="kewarisan")


def test_clean_translation():
    assert clean_translation("dua orang anak perempuan.181) Dan jika") == \
        "dua orang anak perempuan. Dan jika"
    assert clean_translation("diri mereka 86) menurut cara") == \
        "diri mereka menurut cara"
    assert clean_translation("ayat (1) tetap") == "ayat (1) tetap"
    assert clean_translation("(mewajibkan)") == "(mewajibkan)"
    assert clean_translation("(12)") == "(12)"


def test_selection_covers_inheritance_verses():
    covered = {(s, a) for s, first, last, _ in QURAN_SELECTION for a in range(first, last + 1)}
    assert {(4, 11), (4, 12), (4, 176), (65, 1), (2, 228)} <= covered


def test_parse_quran_selected_only():
    ara = {"quran": [{"chapter": 4, "verse": 11, "text": "يُوصِيكُمُ اللَّهُ"},
                     {"chapter": 1, "verse": 1, "text": "بِسْمِ"}]}
    ind = {"quran": [{"chapter": 4, "verse": 11, "text": "Allah mensyariatkan.181) Dan"},
                     {"chapter": 1, "verse": 1, "text": "Dengan nama Allah"}]}
    [chunk] = parse_quran(ara, ind, _src("quran-ara"), _src("quran-ind"))
    assert chunk.chunk_id == "quran:4:11"
    assert chunk.citation == "QS An-Nisa [4]: 11"
    assert chunk.text == "Allah mensyariatkan. Dan"
    assert chunk.text_ar == "يُوصِيكُمُ اللَّهُ"
    assert chunk.domain == "kewarisan" and chunk.source_type == "quran"
    assert chunk.license == "lic-quran-ara; terjemahan: lic-quran-ind"
    assert chunk.hierarchy == {"surah": "4", "ayat": "11"}
