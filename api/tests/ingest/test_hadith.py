from app.ingest.hadith import normalize_grade, parse_hadith, section_domain
from app.ingest.sources import Source


def _src(doc_id):
    return Source(doc_id=doc_id, judul=doc_id, singkatan="HR", jenis="hadis",
                  url_sumber=f"https://cdn.example/{doc_id}.json", format="json",
                  lisensi=f"lic-{doc_id}", domain="kewarisan")


def test_section_domain():
    assert section_domain("Laws of Inheritance (Al-Faraa'id)") == "kewarisan"
    assert section_domain("Shares of Inheritance (Kitab Al-Fara'id)") == "kewarisan"
    assert section_domain("Wills (Kitab Al-Wasaya)") == "kewarisan"
    assert section_domain("The Book on Divorce and Li'an") == "perceraian"
    assert section_domain("The Book of Suckling") == "perkawinan"
    assert section_domain("The Book of al-Fara' and al-'Atirah") is None
    assert section_domain("The Book of Prayer") is None


def test_normalize_grade():
    assert normalize_grade("bukhari", []) == "sahih"
    assert normalize_grade("abudawud", [{"name": "X", "grade": "Hasan"},
                                        {"name": "Al-Albani", "grade": "Da'if"}]) == "dhaif"
    assert normalize_grade("tirmidhi", [{"name": "Al-Albani", "grade": "Hasan Sahih"}]) == "sahih"
    assert normalize_grade("nasai", [{"name": "Other", "grade": "Hasan"}]) == "hasan"
    assert normalize_grade("ibnmajah", []) == "tidak_diketahui"


def test_parse_hadith_joins_by_number_arabic_only():
    """Public hadith chunks are Arabic matn only (spec Sec 4.1): the Indonesian
    editions are unverifiable (author: Unknown, source: "") and never used."""
    info = {"abudawud": {
        "metadata": {"sections": {"19": "Shares of Inheritance (Kitab Al-Fara'id)",
                                  "1": "Purification"}},
        "hadiths": [{"hadithnumber": 2894, "grades": [{"name": "Al-Albani", "grade": "Sahih"}],
                     "reference": {"book": 19, "hadith": 1}},
                    {"hadithnumber": 5, "grades": [], "reference": {"book": 1, "hadith": 5}}],
    }}
    ara = {"hadiths": [{"hadithnumber": 5, "text": "طهارة", "reference": {"book": 1, "hadith": 5}},
                       {"hadithnumber": 2894, "text": " الجدة ", "reference": {"book": 19, "hadith": 1}}]}
    [chunk] = parse_hadith("abudawud", ara, info, _src("hadis-abudawud-ara"))
    assert chunk.chunk_id == "hadith:abudawud:2894"
    assert chunk.doc_id == "hadis-abudawud"
    assert chunk.citation == "HR. Abu Dawud no. 2894"
    assert chunk.text == "الجدة"
    assert chunk.text_ar == "الجدة"
    assert chunk.domain == "kewarisan"
    assert chunk.hadith.derajat == "sahih" and chunk.hadith.nomor == "2894"
    assert chunk.hadith.kitab == "Sunan Abu Dawud"
    assert chunk.source_url == "https://cdn.example/hadis-abudawud-ara.json"
    assert chunk.license == "lic-hadis-abudawud-ara"


def test_decimal_hadithnumber_non_muslim_collection():
    """Non-muslim collections keep hadithnumber-based nomor unchanged (reviewer
    confirmed hadithnumber == arabicnumber for the other five collections)."""
    info = {"nasai": {"metadata": {"sections": {"18": "The Book of Divorce "}},
                      "hadiths": [{"hadithnumber": 1480.5, "grades": [],
                                   "reference": {"book": 18, "hadith": 3}}]}}
    ara = {"hadiths": [{"hadithnumber": 1480.5, "text": "نص", "reference": {"book": 18, "hadith": 3}}]}
    [chunk] = parse_hadith("nasai", ara, info, _src("a"))
    assert chunk.chunk_id == "hadith:nasai:1480-5"
    assert chunk.text == "نص"
    assert chunk.domain == "perceraian"


def test_skip_empty_arabic_text():
    """Regression: skip entries with empty Arabic text; normal entries still yield chunks."""
    info = {"tirmidhi": {"metadata": {"sections": {"18": "The Book of Divorce"}},
                        "hadiths": [{"hadithnumber": 388, "grades": [], "reference": {"book": 18, "hadith": 1}},
                                    {"hadithnumber": 389, "grades": [], "reference": {"book": 18, "hadith": 2}}]}}
    ara = {"hadiths": [{"hadithnumber": 388, "text": "  ", "reference": {"book": 18, "hadith": 1}},
                       {"hadithnumber": 389, "text": "نص", "reference": {"book": 18, "hadith": 2}}]}
    chunks = parse_hadith("tirmidhi", ara, info, _src("a"))
    assert len(chunks) == 1
    assert chunks[0].chunk_id == "hadith:tirmidhi:389"
    assert chunks[0].text == "نص"


def _muslim_entry(hadithnumber, arabicnumber, text, book=18):
    return {
        "hadithnumber": hadithnumber, "arabicnumber": arabicnumber, "grades": [],
        "reference": {"book": book, "hadith": hadithnumber},
    }, {"hadithnumber": hadithnumber, "text": text, "reference": {"book": book, "hadith": hadithnumber}}


def test_muslim_merges_chain_variants_by_abdul_baqi_number():
    """Sahih Muslim's hadithnumber is hadith-api's own sequential count, not
    lookup-able (e.g. hadithnumber 4140 = Abdul Baqi no. 1614 in the real
    data). Several hadithnumbers can share one Abdul Baqi ("arabicnumber")
    base when they are isnad-only chain variants of the same hadith text —
    those must merge into one chunk per Abdul Baqi number, in order."""
    e1, a1 = _muslim_entry(3398, "1400.01", "chain one")
    e2, a2 = _muslim_entry(3399, "1400.02", "chain two")
    e3, a3 = _muslim_entry(3403, "1401", "standalone")
    info = {"muslim": {"metadata": {"sections": {"18": "The Book of Divorce"}},
                       "hadiths": [e1, e2, e3]}}
    ara = {"hadiths": [a1, a2, a3]}
    chunks = {c.chunk_id: c for c in parse_hadith("muslim", ara, info, _src("a"))}
    assert set(chunks) == {"hadith:muslim:1400", "hadith:muslim:1401"}
    assert chunks["hadith:muslim:1400"].text == "chain one\n\nchain two"
    assert chunks["hadith:muslim:1400"].citation == "HR. Muslim no. 1400"
    assert chunks["hadith:muslim:1400"].hadith.nomor == "1400"
    assert chunks["hadith:muslim:1401"].text == "standalone"


def test_muslim_skips_group_with_no_non_empty_text():
    e1, a1 = _muslim_entry(388, "154.02", "")
    info = {"muslim": {"metadata": {"sections": {"18": "The Book of Divorce"}}, "hadiths": [e1]}}
    ara = {"hadiths": [a1]}
    assert parse_hadith("muslim", ara, info, _src("a")) == []


def test_muslim_skips_entry_missing_arabicnumber():
    """No silent merge-into-wrong-group: an entry without arabicnumber is dropped,
    not guessed at (real data has 0 such entries within the family-law subset,
    but the wider muslim edition does have some)."""
    entry = {"hadithnumber": 1, "grades": [], "reference": {"book": 18, "hadith": 1}}
    info = {"muslim": {"metadata": {"sections": {"18": "The Book of Divorce"}}, "hadiths": [entry]}}
    ara = {"hadiths": [{"hadithnumber": 1, "text": "نص", "reference": {"book": 18, "hadith": 1}}]}
    assert parse_hadith("muslim", ara, info, _src("a")) == []
