import httpx
import pytest

from app.ingest.hadeethenc import fetch_snapshot, parse_hadeethenc
from app.ingest.sources import Source

ONE = {
    "10": {"id": "10", "hadeeth": "Abu Hurairah -raḍiyallāhu 'anhu- meriwayatkan, \"Talak.\"",
           "hadeeth_intro": "Abu Hurairah -raḍiyallāhu 'anhu- meriwayatkan,",
           "hadeeth_ar": "نص", "attribution": "Muttafaq 'alaih", "grade": "Hadis sahih",
           "explanation": "Penjelasan singkat."},
    "11": {"id": "11", "hadeeth": "Nikahilah wanita karena agamanya.", "hadeeth_intro": "",
           "hadeeth_ar": "", "attribution": "HR. Muslim", "grade": "Hasan", "explanation": ""},
}
LISTS = {"192": [{"id": "10"}], "191": [{"id": "10"}, {"id": "11"}]}


def _handler(request: httpx.Request) -> httpx.Response:
    params = dict(request.url.params)
    if request.url.path.endswith("/hadeeths/list/"):
        data = LISTS.get(params["category_id"], [])
        return httpx.Response(200, json={"data": data,
                                         "meta": {"current_page": "1", "last_page": 1}})
    if request.url.path.endswith("/hadeeths/one/"):
        return httpx.Response(200, json=ONE[params["id"]])
    return httpx.Response(404)


def _source():
    return Source(doc_id="hadeethenc-id", judul="HadeethEnc", singkatan="HadeethEnc",
                  jenis="hadis", url_sumber="https://hadeethenc.com/api/v1/", fetcher="hadeethenc",
                  format="json", lisensi="HadeethEnc.com terms", domain="perkawinan")


def test_fetch_snapshot_assigns_first_matching_domain():
    with httpx.Client(transport=httpx.MockTransport(_handler)) as client:
        snap = fetch_snapshot(client)
    assert [(h["id"], h["_domain"]) for h in snap["hadeeths"]] == [
        ("10", "perceraian"), ("11", "perkawinan")]
    assert snap["language"] == "id" and len(snap["fetched"]) == 10


def test_parse_hadeethenc():
    snap = {"fetched": "2026-09-27", "hadeeths": [
        {**ONE["10"], "_category": "192", "_domain": "perceraian"},
        {**ONE["11"], "_category": "191", "_domain": "perkawinan"}]}
    first, second = parse_hadeethenc(snap, _source())
    assert first.chunk_id == "hadith:hadeethenc:10"
    assert first.citation == "Muttafaq 'alaih (HadeethEnc no. 10)"
    assert first.text == ONE["10"]["hadeeth"] + "\n\nPenjelasan: Penjelasan singkat."
    assert first.text_ar == "نص"
    assert first.hadith.perawi == "Abu Hurairah" and first.hadith.derajat == "sahih"
    assert first.source_url == "https://hadeethenc.com/id/browse/hadith/10"
    assert first.license.endswith("versi 2026-09-27")
    assert second.text == "Nikahilah wanita karena agamanya."
    assert second.text_ar is None and second.hadith.perawi is None
    assert second.hadith.derajat == "hasan" and second.domain == "perkawinan"


def _one(**fields):
    base = {"id": "1", "hadeeth": "x", "hadeeth_intro": "", "hadeeth_ar": "", "attribution":
            "HR. Muslim", "grade": "Sahih", "explanation": "", "hints": [],
            "_category": "191", "_domain": "perkawinan"}
    return {**base, **fields}


def test_hints_kept_verbatim():
    snap = {"fetched": "2026-10-02", "hadeeths": [_one(
        hadeeth="Teks hadis.", explanation="Penjelasan.",
        hints=["1- Pelajaran pertama.\r", "2- Pelajaran kedua.\r", " "])]}
    [chunk] = parse_hadeethenc(snap, _source())
    assert chunk.text == ("Teks hadis.\n\nPenjelasan: Penjelasan.\n\nPelajaran:\n"
                          "1- Pelajaran pertama.\n2- Pelajaran kedua.")


def test_perawi_from_hadith_text_when_intro_empty():
    texts = {
        "Dari Jābir bin Abdullah, ia berkata, Rasulullah bersabda": "Jābir bin Abdullah",
        "Dari Aisyah -raḍiyallāhu 'anhā- bahwa Nabi": "Aisyah",
        "Ibnu 'Abbās meriwayatkan bahwa seorang gadis": "Ibnu 'Abbās",
        "Dari 'Imrān bin Ḥuṣain bahwasannya dia ditanya": "'Imrān bin Ḥuṣain",
        "Nabi -ṣallallāhu 'alaihi wa sallam- melarang nikah mut'ah": None,
    }
    snap = {"fetched": "2026-10-02",
            "hadeeths": [_one(id=str(i), hadeeth=t) for i, t in enumerate(texts)]}
    got = [c.hadith.perawi for c in parse_hadeethenc(snap, _source())]
    assert got == list(texts.values())


# Real opening sentences from the snapshot: (hadeeth, expected perawi). Precision over recall.
REAL_OPENINGS = [
    ('Dari \'Uqbah bin Āmir ia berkata: Rasulullah -ṣallallāhu \'alaihi wa sallam- bersabda, "Sebaik-baik pe', "'Uqbah bin Āmir"),  # 58110
    ("Dari 'Urwah, ia berkata, “Aisyah -raḍiyallāhu 'anhā- berkata, “Wahai putra saudariku, Rasulullah -ṣa", None),  # 58129
    ('Dari Ibnu \'Abbās ia berkata, "Abdu Yazīd ayah Rukānah dan ayah saudara-saudaranya telah menceraikan ', "Ibnu 'Abbās"),  # 58140
    ('Dari Ibnu Umar ia berkata, “Jika sudah berlalu selama empat bulan, (maka suami yang melakukan ilā`) ', 'Ibnu Umar'),  # 58151
    ('Dari Ummu Salamah ia berkata, Rasulullah -ṣallallāhu \'alaihi wa sallam- bersabda, "Persusuan tidak b', 'Ummu Salamah'),  # 58177
    ("Dari 'Āmir bin Abdillah bin az-Zubair, dari bapaknya, bahwa Nabi -ṣallallāhu 'alaihi wa sallam- bers", None),  # 58065
    ('Dari Iyās bin Salamah, dari bapaknya, ia berkata, "Rasulullah -ṣallallāhu \'alaihi wa sallam- membole', None),  # 58075
    ('Dari Aḍ-Ḍaḥḥāk bin Fairūz, dari ayahnya, ia berkata, Fairuz berkata, saya saya bertanya, "Wahai Rasu', None),  # 58082
    ('Dari \'Amr bin Syu\'aib, dari bapaknya, dari kakeknya, ia berkata, "Rasulullah -ṣallallāhu \'alaihi wa ', None),  # 58147
    ("Dari Ibnu Syihāb bahwa Sahl bin Sa'ad As-Sā'idī memberitahunya, bahwasanya 'Uwaimir Al-'Ajlānī menda", None),  # 58157
    ("Dari 'Urwah bin Zubair, dari Aisyah istri Nabi -ṣallallāhu 'alaihi wa sallam- bahwa dirinya telah me", None),  # 58167
    ('Dari Abu Salamah bin Abdirrahman, bahwasannya dia berkata, "Aku bertanya kepada Aisyah, istri Nabi -', None),  # 58103
    ('Dari \'Alqamah dan al-Aswad, keduanya berkata, "Ada seorang laki-laki yang dibawa ke hadapan Abdullah', None),  # 58106
    ("Dari 'Imrān bin Ḥuṣain bahwasannya dia ditanya tentang seseorang yang menceraikan istrinya lalu meny", "'Imrān bin Ḥuṣain"),  # 58149
    ('Dari Ibnu Umar bahwasannya dia berkata, "(Batasan) talak seorang suami yang berstatus budak kepada i', 'Ibnu Umar'),  # 58168
    ('Dari Ibnu \'Abbās -raḍiyallāhu \'anhumā-, bahwasanya Ali berkata, "Aku telah menikahi Fatimah -raḍiyal', "Ibnu 'Abbās"),  # 58104
    ("Dari Subai'ah al-Aslamiyah, dahulu dia adalah isteri dari Sa'ad bin Khaulah -dari Bani 'Āmir bin Lu`", "Subai'ah al-Aslamiyah"),  # 6046
]


@pytest.mark.parametrize(("text", "expected"), REAL_OPENINGS)
def test_perawi_real_openings(text, expected):
    snap = {"fetched": "2026-10-02", "hadeeths": [_one(hadeeth=text)]}
    [chunk] = parse_hadeethenc(snap, _source())
    assert chunk.hadith.perawi == expected
