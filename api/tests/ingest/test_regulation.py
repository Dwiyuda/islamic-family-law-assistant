import pytest

from app.ingest.regulation import deleted_pasal, mark_amendments, parse_regulation
from app.ingest.sources import Source

TEXT = """PRESIDEN REPUBLIK INDONESIA
Menimbang : a. bahwa ...
BUKU I
HUKUM PERKAWINAN
BAB I
KETENTUAN UMUM
Pasal 1
Perkawinan ialah ikatan lahir batin.
BAB XVI
PUTUSNYA PERKAWINAN
Bagian Kesatu
Umum
Pasal 116
Perceraian dapat terjadi karena alasan:
a. salah satu pihak berbuat zina;
Pasal 7A
Isi pasal sisipan.
BUKU III
HUKUM PERWAKAFAN
BAB I
Pasal 215
Wakaf adalah ...
PENJELASAN
Pasal 1
Cukup jelas.
"""


def _src(**over):
    data = {
        "doc_id": "khi-1991", "judul": "Kompilasi Hukum Islam", "singkatan": "KHI",
        "jenis": "inpres", "url_sumber": "https://x.go.id/khi.pdf", "format": "pdf",
        "lisensi": "public-domain", "domain": "perkawinan", "status": "berlaku",
        "domain_rules": [{"buku": "I", "bab": "XVI", "domain": "perceraian"},
                          {"buku": "III", "domain": "skip"}],
    }
    data.update(over)
    return Source(**data)


def test_basic_structure():
    chunks = parse_regulation(TEXT, _src())
    assert [c.chunk_id for c in chunks] == [
        "khi-1991:pasal-1", "khi-1991:pasal-116", "khi-1991:pasal-7a",
    ]
    first, cerai, sisipan = chunks
    assert first.text == "Pasal 1\nPerkawinan ialah ikatan lahir batin."
    assert first.domain == "perkawinan"
    assert first.hierarchy == {"buku": "I", "bab": "I", "bagian": None, "pasal": "1", "ayat": None}
    assert cerai.domain == "perceraian"
    assert cerai.hierarchy["bagian"] == "kesatu"
    assert cerai.citation == "KHI Pasal 116"
    assert "Umum" not in cerai.text
    assert sisipan.citation == "KHI Pasal 7A"
    assert all(c.source_type == "regulation" and c.status == "berlaku" for c in chunks)


def test_long_pasal_split_per_ayat():
    long_body = " ".join(["kata"] * 200)
    text = f"BAB I\nPasal 39\nPembukaan pasal.\n(1) {long_body}\n(2) {long_body}\n"
    chunks = parse_regulation(text, _src(domain_rules=[]))
    assert [c.chunk_id for c in chunks] == ["khi-1991:pasal-39:ayat-1", "khi-1991:pasal-39:ayat-2"]
    assert chunks[0].text.startswith("Pasal 39 ayat (1)\nPembukaan pasal.\n(1) kata")
    assert chunks[1].citation == "KHI Pasal 39 ayat (2)"
    assert chunks[1].hierarchy["ayat"] == "2"


def test_short_pasal_with_ayat_not_split():
    text = "BAB I\nPasal 2\n(1) Pendek satu.\n(2) Pendek dua.\n"
    [chunk] = parse_regulation(text, _src(domain_rules=[]))
    assert chunk.chunk_id == "khi-1991:pasal-2"
    assert chunk.text == "Pasal 2\n(1) Pendek satu.\n(2) Pendek dua."


def test_duplicate_pasal_numbers_get_suffix():
    text = "Pasal I\nBeberapa ketentuan diubah:\nPasal 7\nisi baru\nPasal II\nberlaku\nPasal 7\nlagi\n"
    chunks = parse_regulation(text, _src(doc_id="uu-16-2019", singkatan="UU 16/2019",
                                         domain_rules=[]))
    assert [c.chunk_id for c in chunks] == [
        "uu-16-2019:pasal-i", "uu-16-2019:pasal-7", "uu-16-2019:pasal-ii", "uu-16-2019:pasal-7-2",
    ]


# --- Ruling A: tolerant BUKU/BAB headings with OCR noise, canonical numerals ---


def test_buku_ocr_lowercase_l_normalized_and_dropped_by_skip_rule():
    text = "BUKU Ill\nHUKUM PERWAKAFAN\nBAB I\nPasal 215\nWakaf adalah ...\n"
    chunks = parse_regulation(text, _src(domain_rules=[{"buku": "III", "domain": "skip"}]))
    assert chunks == []


def test_buku_no_space_before_numeral():
    text = "BUKUI\nHUKUM PERKAWINAN\nBAB I\nPasal 1\nIsi.\n"
    [chunk] = parse_regulation(text, _src(domain_rules=[]))
    assert chunk.hierarchy["buku"] == "I"


def test_bab_no_space_before_numeral():
    text = "BUKU I\nBABXVI\nPUTUSNYA PERKAWINAN\nPasal 116\nIsi.\n"
    [chunk] = parse_regulation(text, _src(domain_rules=[]))
    assert chunk.hierarchy["bab"] == "XVI"


def test_bab_ocr_misread_as_bah():
    text = "BAH XVIII\nJUDUL BAB\nPasal 200\nIsi.\n"
    [chunk] = parse_regulation(text, _src(domain_rules=[]))
    assert chunk.hierarchy["bab"] == "XVIII"


def test_bab_ocr_misread_as_bad():
    text = "BAD XIX\nJUDUL BAB\nPasal 201\nIsi.\n"
    [chunk] = parse_regulation(text, _src(domain_rules=[]))
    assert chunk.hierarchy["bab"] == "XIX"


def test_bahwa_badan_and_bab_lain_lines_not_treated_as_headings():
    text = (
        "BAB I\n"
        "BAHWA negara menjamin.\n"
        "BADAN Pertanahan mencatat.\n"
        "BAB lain tidak relevan.\n"
        "Pasal 1\n"
        "Isi pasal.\n"
    )
    [chunk] = parse_regulation(text, _src(domain_rules=[]))
    assert chunk.hierarchy["bab"] == "I"
    assert chunk.text == "Pasal 1\nIsi pasal."


# --- Ruling B: stop at LAMPIRAN, but only after the first Pasal ---


def test_lampiran_after_pasal_stops_parsing():
    text = "BAB I\nPasal 1\nIsi pasal satu.\nLAMPI RAN\nPasal 999\nIni bukan bagian KHI.\n"
    chunks = parse_regulation(text, _src(domain_rules=[]))
    assert [c.chunk_id for c in chunks] == ["khi-1991:pasal-1"]


def test_lampiran_before_first_pasal_is_ignored():
    text = "LAMPIRAN\nDAFTAR ISI\nBAB I\nPasal 1\nIsi pasal.\n"
    [chunk] = parse_regulation(text, _src(domain_rules=[]))
    assert chunk.chunk_id == "khi-1991:pasal-1"
    assert chunk.text == "Pasal 1\nIsi pasal."


# --- Ruling C: real KHI OCR - "Pasal" glued to a numeral with l->1, O->0 noise ---


def test_pasal_glued_no_space_plain_digits():
    text = "BAB I\nPasal2\nIsi dua.\n"
    [chunk] = parse_regulation(text, _src(domain_rules=[]))
    assert chunk.chunk_id == "khi-1991:pasal-2"


def test_pasal_lowercase_l_misread_as_digit_one():
    text = "BAB I\nPasall\nIsi satu.\n"
    [chunk] = parse_regulation(text, _src(domain_rules=[]))
    assert chunk.hierarchy["pasal"] == "1"
    assert chunk.chunk_id == "khi-1991:pasal-1"


def test_pasal_10_ocr_lowercase_l_and_uppercase_o():
    text = "BAB I\nPasallO\nIsi sepuluh.\n"
    [chunk] = parse_regulation(text, _src(domain_rules=[]))
    assert chunk.hierarchy["pasal"] == "10"


def test_pasal_13_ocr_lowercase_l_then_plain_digit():
    text = "BAB I\nPasall3\nIsi tiga belas.\n"
    [chunk] = parse_regulation(text, _src(domain_rules=[]))
    assert chunk.hierarchy["pasal"] == "13"


def test_pasal_11_ocr_two_lowercase_l():
    text = "BAB I\nPasalll\nIsi sebelas.\n"
    [chunk] = parse_regulation(text, _src(domain_rules=[]))
    assert chunk.hierarchy["pasal"] == "11"


def test_pasal_word_final_l_misread_as_digit_one():
    # Real KHI OCR: "Pasal 24" -> "Pasa124" (the word "Pasal" itself loses its
    # final "l" to a "1" misread, then plain digits follow with no space).
    text = "BAB I\nPasa124\nIsi dua puluh empat.\n"
    [chunk] = parse_regulation(text, _src(domain_rules=[]))
    assert chunk.hierarchy["pasal"] == "24"


def test_pasal_101_ocr_lowercase_i_and_uppercase_o_and_i():
    # Real KHI OCR: "Pasal 101" -> "PasaliOI" (lowercase i and uppercase I both
    # misread for digit 1, uppercase O misread for digit 0).
    text = "BAB I\nPasaliOI\nIsi seratus satu.\n"
    [chunk] = parse_regulation(text, _src(domain_rules=[]))
    assert chunk.hierarchy["pasal"] == "101"


def test_pasal_roman_numeral_still_preserved_after_ocr_fix():
    # "Pasal I" / "Pasal II" are genuine amendment-article numerals (uppercase
    # roman), not OCR noise - must not be normalized to digits.
    text = "Pasal I\nBeberapa ketentuan diubah:\nPasal II\nberlaku\n"
    chunks = parse_regulation(text, _src(doc_id="uu-16-2019", singkatan="UU 16/2019",
                                         domain_rules=[]))
    assert [c.chunk_id for c in chunks] == ["uu-16-2019:pasal-i", "uu-16-2019:pasal-ii"]


def test_pasal_reference_inside_body_not_matched_as_heading():
    text = ("BAB I\nPasal 1\nSebagaimana diatur dalam Pasal 49 ayat (1) huruf a "
            "peraturan ini.\n")
    [chunk] = parse_regulation(text, _src(domain_rules=[]))
    assert chunk.chunk_id == "khi-1991:pasal-1"
    assert "Pasal 49" in chunk.text


# --- Ruling D: PENJELASAN in the KHI table of contents (daftar isi), before any
# Pasal, must not stop parsing before the real content even starts ---


def test_penjelasan_in_toc_before_first_pasal_is_ignored():
    text = (
        "PENJELASAN ATAS\n"
        "BUKU KOMPILASI HUKUM ISLAM ........ 123\n"
        "BUKU I\nBAB I\nPasal 1\nIsi pasal.\n"
        "PENJELASAN\nPasal 1\nCukup jelas.\n"
    )
    chunks = parse_regulation(text, _src(domain_rules=[]))
    assert [c.chunk_id for c in chunks] == ["khi-1991:pasal-1"]
    assert chunks[0].text == "Pasal 1\nIsi pasal."


# --- ayat over-split: PDF line-wrap leaves a body line starting with "(N)" ---


def test_ayat_line_wrap_false_positive_not_treated_as_new_ayat():
    long_body = " ".join(["kata"] * 200)
    text = (
        "BAB I\nPasal 17\n"
        f"(1) {long_body}\n"
        "(2) Kehadiran Para Pihak sebagaimana dimaksud pada ayat\n"
        f"(1) berdasarkan panggilan yang sah dan patut. {long_body}\n"
    )
    chunks = parse_regulation(text, _src(domain_rules=[]))
    assert [c.chunk_id for c in chunks] == [
        "khi-1991:pasal-17:ayat-1", "khi-1991:pasal-17:ayat-2",
    ]
    assert "berdasarkan panggilan" in chunks[1].text


# --- Task 2: page chrome, catchwords, closing formula, text_corrections ---


def _reg_source(**overrides):
    fields = {
        "doc_id": "uu-x", "judul": "UU X", "singkatan": "UU X", "jenis": "uu",
        "url_sumber": "https://peraturan.example.go.id/x.pdf", "format": "pdf",
        "lisensi": "public-domain", "domain": "perkawinan",
    }
    return Source(**{**fields, **overrides})


def test_page_chrome_and_catchwords_dropped():
    text = ("Pasal 1\nIsi pasal satu.\nPasal 2 …\nPRESIDEN\nREPUBLIK INDONESIA\n"
            "www.djpp.depkumham.go.id\nPasal 2\nIsi dua.\n(3) Ketentuan- ...\nlanjutan.\n")
    chunks = parse_regulation(text, _reg_source())
    assert [c.text for c in chunks] == ["Pasal 1\nIsi pasal satu.", "Pasal 2\nIsi dua.\nlanjutan."]


def test_closing_formula_ends_last_pasal():
    text = ("Pasal 67\nBerlaku sejak diundangkan.\nAgar ...\n"
            "Agar supaya setiap orang dapat mengetahuinya, memerintahkan\npengundangan.\n"
            "Disahkan di Jakarta\nttd\nSOEHARTO\n")
    [chunk] = parse_regulation(text, _reg_source())
    assert chunk.text == "Pasal 67\nBerlaku sejak diundangkan."


def test_text_corrections_whole_word_case_preserving():
    src = _reg_source(text_corrections={"hagian": "bagian", "suarni": "suami"})
    [chunk] = parse_regulation("Pasal 176\nHagian anak untuk suarni, hagiannya tetap.\n", src)
    assert chunk.text == "Pasal 176\nBagian anak untuk suami, hagiannya tetap."


def test_text_corrections_keys_must_be_lowercase():
    import pytest
    with pytest.raises(ValueError):
        _reg_source(text_corrections={"Hagian": "bagian"})


def test_generic_ocr_rules_only_for_ocr_sources():
    text = "Pasal 116\nKarena a1asan atau alasanalasan masingmasing.\n"
    [ocr] = parse_regulation(text, _reg_source(text_corrections={"hagian": "bagian"}))
    assert ocr.text == "Pasal 116\nKarena alasan atau alasan-alasan masing-masing."
    [digital] = parse_regulation(text, _reg_source())
    assert digital.text == "Pasal 116\nKarena a1asan atau alasanalasan masingmasing."


def test_text_corrections_apostrophe_key_matches_whole_word_only():
    # Fix round 1: a bare "bal": "hal" key corrupted "talak bal'in" (an OCR misread of
    # "talak ba'in") into "talak hal'in", because the apostrophe is a \b word boundary
    # for the whole-word regex. The key must be the full apostrophe-containing token.
    src = _reg_source(text_corrections={"bal'in": "ba'in"})
    [chunk] = parse_regulation("Pasal 1\nIsteri dijatuhi talak bal'in atau nusyuz.\n", src)
    assert chunk.text == "Pasal 1\nIsteri dijatuhi talak ba'in atau nusyuz."
    [unrelated] = parse_regulation("Pasal 1\nIni adalah balasan yang setimpal.\n", src)
    assert unrelated.text == "Pasal 1\nIni adalah balasan yang setimpal."


# --- Task 3: amendment laws - strip instructions, mark amended pasal, reword citations ---


def test_amendment_instructions_stripped_and_pasal_marked():
    base = _reg_source(doc_id="uu-1-1974", singkatan="UU 1/1974", status="diubah")
    amend = _reg_source(doc_id="uu-16-2019", singkatan="UU 16/2019", status="berlaku",
                        amends="uu-1-1974")
    chunks = parse_regulation("Pasal 6\nSyarat.\nPasal 7\nUmur 16.\n", base) + parse_regulation(
        "Pasal I\nBeberapa ketentuan diubah:\nPasal 7\nUmur 19.\n"
        "1. Di antara Pasal 65 dan Pasal 66 disisipkan\nsatu pasal:\n"
        "Pasal 65A\nBaru.\nPasal II\nBerlaku.\n", amend)
    out = {c.chunk_id: c for c in mark_amendments(chunks, {"uu-1-1974": base,
                                                            "uu-16-2019": amend})}
    assert out["uu-1-1974:pasal-7"].status == "diubah"
    assert out["uu-1-1974:pasal-7"].hierarchy["diubah_oleh"] == "UU 16/2019"
    assert out["uu-1-1974:pasal-6"].status == "berlaku"
    assert "diubah_oleh" not in out["uu-1-1974:pasal-6"].hierarchy
    assert out["uu-16-2019:pasal-7"].text == "Pasal 7\nUmur 19."
    assert out["uu-16-2019:pasal-7"].citation == "UU 1/1974 Pasal 7 sebagaimana diubah UU 16/2019"
    assert out["uu-16-2019:pasal-65a"].citation == (
        "UU 1/1974 Pasal 65A sebagaimana diubah UU 16/2019")
    assert out["uu-16-2019:pasal-i"].citation == "UU 16/2019 Pasal I"


def test_numbered_lines_in_ordinary_laws_are_kept():
    text = "Pasal 3\n1. Ketentuan umum berlaku.\n2. Lainnya.\n"
    [chunk] = parse_regulation(text, _reg_source())
    assert chunk.text == "Pasal 3\n1. Ketentuan umum berlaku.\n2. Lainnya."


# --- Fix round 1: repealed pasal + chained amendments (status by latest event, by tahun) ---


def test_deleted_pasal_matches_real_phrasing():
    # Real phrasing found in data/raw/uu-3-2006.pdf and data/raw/uu-50-2009.pdf.
    assert deleted_pasal("34. Ketentuan Pasal 46 dihapus.\n") == {"46"}
    assert deleted_pasal("18. Ketentuan Pasal 44 dihapus.\n") == {"44"}
    # A sub-item deletion ("b. dihapus.") or a narrative mention of "dihapus" is not a
    # whole-pasal deletion instruction and must not be picked up.
    assert deleted_pasal("b. dihapus . . .\n\nb. dihapus.\n") == set()
    assert deleted_pasal(
        "dipergunakan dalam pembagian warisan”, dinyatakan dihapus.\n") == set()


def test_chained_amendments_use_latest_event_by_tahun():
    base = _reg_source(doc_id="uu-base", singkatan="UU Base", status="diubah")
    first = _reg_source(doc_id="uu-first", singkatan="UU First", status="berlaku",
                        amends="uu-base", tahun=2006)
    second = _reg_source(doc_id="uu-second", singkatan="UU Second", status="berlaku",
                         amends="uu-base", tahun=2009)
    base_chunks = parse_regulation("Pasal 1\nAsal satu.\nPasal 2\nAsal dua.\n", base)
    first_chunks = parse_regulation(
        "1. Ketentuan Pasal 1 diubah sehingga berbunyi:\nPasal 1\nUbah pertama satu.\n"
        "2. Ketentuan Pasal 2 diubah sehingga berbunyi:\nPasal 2\nUbah pertama dua.\n",
        first,
    )
    second_text = (
        "1. Ketentuan Pasal 1 dihapus.\n"
        "2. Ketentuan Pasal 2 diubah sehingga berbunyi:\nPasal 2\nUbah kedua dua.\n"
    )
    second_chunks = parse_regulation(second_text, second)
    sources = {"uu-base": base, "uu-first": first, "uu-second": second}
    deletions = {"uu-second": deleted_pasal(second_text)}

    out = {c.chunk_id: c for c in mark_amendments(
        base_chunks + first_chunks + second_chunks, sources, deletions)}

    # Base law: latest event per pasal wins.
    assert out["uu-base:pasal-1"].status == "dicabut"
    assert out["uu-base:pasal-1"].hierarchy["dicabut_oleh"] == "UU Second"
    assert "diubah_oleh" not in out["uu-base:pasal-1"].hierarchy
    assert out["uu-base:pasal-2"].status == "diubah"
    assert out["uu-base:pasal-2"].hierarchy["diubah_oleh"] == "UU First, UU Second"

    # Earlier amendment chunk (UU First, 2006) is itself superseded by the later
    # amendment (UU Second, 2009): the pasal it re-issued was later deleted or re-issued
    # again.
    assert out["uu-first:pasal-1"].status == "dicabut"
    assert out["uu-first:pasal-1"].hierarchy["dicabut_oleh"] == "UU Second"
    assert out["uu-first:pasal-2"].status == "diubah"
    assert out["uu-first:pasal-2"].hierarchy["diubah_oleh"] == "UU Second"

    # Latest amendment chunk (UU Second, 2009) is not superseded by anything: berlaku.
    assert out["uu-second:pasal-2"].status == "berlaku"
    assert "uu-second:pasal-1" not in out  # deletion instruction re-issues nothing


def test_fuzzy_page_chrome_dropped():
    text = ("Pasal 7\n(1) Umur 19 tahun.\nSK No 006?66 A\ntrRESIDEN\nREPUBLIK' INDONESIA\n"
            "(2) Dispensasi.\nPasal 8\nIsi.\nAgar\n")
    chunks = parse_regulation(text, _reg_source())
    assert chunks[0].text == "Pasal 7\n(1) Umur 19 tahun.\n(2) Dispensasi."
    assert chunks[1].text == "Pasal 8\nIsi."


def test_glued_reduplication_with_suffix():
    src = _reg_source(text_corrections={"hagian": "bagian"})
    [chunk] = parse_regulation("Pasal 1\nbiaya untuk anakanaknya dan akibatakibatnya.\n", src)
    assert chunk.text == "Pasal 1\nbiaya untuk anak-anaknya dan akibat-akibatnya."


def test_text_replacements_span_lines_and_must_match():
    src = _reg_source(text_replacements={"yang\nseluruhnya": "yang masih terhutang seluruhnya",
                                         "urn urn": "umum"})
    text = "Pasal 1\nmelunasi mahar yang\nseluruhnya.\nPasal 2\nkesejahteraan urn urn.\n"
    first, second = parse_regulation(text, src)
    assert first.text == "Pasal 1\nmelunasi mahar yang masih terhutang seluruhnya."
    assert second.text == "Pasal 2\nkesejahteraan umum."
    with pytest.raises(ValueError, match="never matched"):
        parse_regulation(text, _reg_source(text_replacements={"tidak ada": "x"}))


def test_footnote_moves_to_its_pasal():
    src = _reg_source(footnote_moves={"185": "177"})
    text = ("Pasal 177\nAyah mendapat sepertiga.\nPasal 185\n(1) Ahli waris pengganti.\n"
            "* Berdasarkan SEMA 2/1994 ayah\nmendapat sepertiga.\n(2) Bagian pengganti.\n")
    p177, p185 = parse_regulation(text, src)
    assert p177.text == ("Pasal 177\nAyah mendapat sepertiga.\n"
                         "* Berdasarkan SEMA 2/1994 ayah\nmendapat sepertiga.")
    assert p185.text == "Pasal 185\n(1) Ahli waris pengganti.\n(2) Bagian pengganti."
    with pytest.raises(ValueError):
        parse_regulation("Pasal 177\nIsi.\nPasal 185\nTanpa catatan.\n", src)


def test_footnote_moves_target_pasal_missing_raises():
    src = _reg_source(footnote_moves={"185": "999"})
    text = "Pasal 185\n(1) Ahli waris pengganti.\n* Berdasarkan SEMA 2/1994 catatan.\n"
    with pytest.raises(ValueError, match="not moved to Pasal 999"):
        parse_regulation(text, src)
