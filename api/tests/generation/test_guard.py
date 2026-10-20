from app.generation.guard import GuardStats, guard_answer, guard_steps
from app.generation.schemas import AskDraft, Langkah, NavigatorResponse
from app.generation.sources import CHUNK_NOTES, notes_for, order_by_authority, to_sumber
from app.ingest.models import Chunk, HadithMeta


def _c(cid, source_type="regulation", status="berlaku", derajat=None):
    return Chunk(chunk_id=cid, doc_id=cid.split(":")[0], doc_title="Doc", source_type=source_type,
                 domain="perceraian", citation=cid.upper(), text="teks",
                 source_url="https://x.go.id", license="public-domain",
                 status=status if source_type == "regulation" else None,
                 hadith=(HadithMeta(kitab="K", nomor="1", derajat=derajat)
                         if source_type == "hadith" else None))


CH = {c.chunk_id: c for c in [
    _c("khi:pasal-1"), _c("uu:pasal-2", status="diubah"), _c("uu:pasal-3", status="dicabut"),
    _c("quran:4:11", "quran"), _c("hadith:a:1", "hadith", derajat="sahih"),
    _c("hadith:b:2", "hadith", derajat="dhaif"),
    _c("hadith:c:3", "hadith", derajat="tidak_diketahui"),
    _c("prosedur:langkah-1", "procedure"),
]}


def test_authority_order_is_stable_within_a_tier():
    ids = ["hadith:b:2", "hadith:a:1", "quran:4:11", "prosedur:langkah-1", "uu:pasal-3",
           "khi:pasal-1", "uu:pasal-2"]
    assert order_by_authority(ids, CH) == [
        "khi:pasal-1", "uu:pasal-2", "prosedur:langkah-1", "quran:4:11", "hadith:a:1",
        "hadith:b:2", "uu:pasal-3"]


def test_guard_steps_drops_invented_and_weak_only_steps():
    steps = [
        Langkah(urutan=1, judul="A", uraian="a", sitasi=["khi:pasal-1", "khi:pasal-999"]),
        Langkah(urutan=2, judul="B", uraian="b", sitasi=["hadith:b:2"]),
        Langkah(urutan=3, judul="C", uraian="c", sitasi=["hadith:b:2", "quran:4:11"]),
        Langkah(urutan=4, judul="D", uraian="d", sitasi=["uu:pasal-3", "hadith:c:3"]),
        Langkah(urutan=5, judul="E", uraian="e", sitasi=["tidak:ada"]),
    ]
    retrieved = ["khi:pasal-1", "hadith:b:2", "quran:4:11", "uu:pasal-3", "hadith:c:3"]
    kept, stats = guard_steps(steps, retrieved, CH)
    assert [s.judul for s in kept] == ["A", "C"]
    assert [s.urutan for s in kept] == [1, 2]
    assert kept[0].sitasi == ["khi:pasal-1"]
    assert stats == GuardStats(citations_total=8, citations_valid=6, steps_total=5,
                               steps_kept=2)


def test_guard_answer_dedupes_and_rejects_weak_only():
    good, stats = guard_answer(["khi:pasal-1", "khi:pasal-1", "x:y"], ["khi:pasal-1"], CH)
    assert good == ["khi:pasal-1"]
    assert stats == GuardStats(citations_total=3, citations_valid=2, steps_total=1,
                               steps_kept=1)
    assert guard_answer(["hadith:b:2"], ["hadith:b:2"], CH)[0] == []


def test_notes_for_status_and_owner_notes(monkeypatch):
    monkeypatch.setitem(CHUNK_NOTES, "khi:pasal-1", "Catatan MK.")
    assert notes_for(["khi:pasal-1", "uu:pasal-2", "uu:pasal-3", "quran:4:11"], CH) == [
        "Catatan MK.",
        ("UU:PASAL-2 telah diubah oleh peraturan yang lebih baru; periksa bunyi pasal "
         "perubahannya."),
        "UU:PASAL-3 sudah dicabut dan tidak berlaku lagi.",
    ]


def test_to_sumber_carries_grade_and_status():
    assert to_sumber(CH["hadith:b:2"]).derajat == "dhaif"
    assert to_sumber(CH["uu:pasal-2"]).status == "diubah"
    assert to_sumber(CH["quran:4:11"]).derajat is None


def test_schema_defaults():
    r = NavigatorResponse(status="ditolak", ringkasan="x", mode="llm")
    assert "bukan pengganti advokat" in r.disclaimer and r.langkah == [] and r.sumber == []
    assert AskDraft.model_validate({"status": "di_luar_cakupan"}).sitasi == []


def test_owner_verified_mk_notes_point_at_real_chunks():
    from app.retrieval.corpus import REPO_ROOT, load_corpus

    assert "46/PUU-VIII/2010" in CHUNK_NOTES["uu-1-1974:pasal-43"]
    assert "69/PUU-XIII/2015" in CHUNK_NOTES["uu-1-1974:pasal-29"]
    assert set(CHUNK_NOTES) <= {c.chunk_id for c in load_corpus(REPO_ROOT / "data")}
