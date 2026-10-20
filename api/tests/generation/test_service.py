import hashlib
from pathlib import Path

from app.generation.fakes import FakeProvider
from app.generation.prompts import PROMPT_VERSION, SYSTEM, context_block, messages
from app.generation.providers import ProviderError, ProviderUnavailable
from app.generation.service import NAVIGATOR_DOMAINS, Assistant
from app.retrieval.retriever import Hit

NAV_Q = "Suami melanggar taklik talak, saya ingin cerai"
ASK_Q = "berapa bagian anak perempuan kalau hanya seorang"
NAV = {"status": "ok", "jenis_perkara": "cerai_gugat",
       "pengadilan": "Pengadilan Agama tempat tinggal Penggugat",
       "ringkasan": "Istri dapat mengajukan cerai gugat.",
       "langkah": [{"urutan": 1, "judul": "Siapkan alasan", "uraian": "Taklik talak.",
                    "dokumen": ["Buku nikah"], "sitasi": ["khi-1991:pasal-116"]},
                   {"urutan": 2, "judul": "Karangan", "uraian": "Tanpa dasar.",
                    "sitasi": ["khi-1991:pasal-999"]}],
       "peringatan": []}
ASK = {"status": "ok", "jawaban": "Anak perempuan tunggal mendapat separoh.",
       "sitasi": ["khi-1991:pasal-176", "khi-1991:pasal-999"]}


def _assistant(retriever, provider):
    return Assistant(retriever.chunks, provider, retriever.search, threshold=0.1)


def test_navigator_guards_citations_and_filters_domains(retriever):
    out = _assistant(retriever, FakeProvider(NAV)).navigator(NAV_Q)
    r = out.response
    assert (r.status, r.mode, r.jenis_perkara) == ("ok", "llm", "cerai_gugat")
    assert [s.judul for s in r.langkah] == ["Siapkan alasan"]
    assert (out.stats.citations_total, out.stats.citations_valid) == (2, 1)
    assert {s.chunk_id for s in r.sumber} <= {"khi-1991:pasal-116", "khi-1991:pasal-149",
                                              "uu-7-1989:pasal-49"}
    assert "bukan pengganti advokat" in r.disclaimer
    assert NAVIGATOR_DOMAINS == {"perceraian", "peradilan", "prosedur"}


def test_ask_keeps_only_retrieved_citations(retriever):
    out = _assistant(retriever, FakeProvider(ASK)).ask(ASK_Q)
    assert out.response.status == "ok" and out.response.sitasi == ["khi-1991:pasal-176"]
    assert out.retrieved[0] == "khi-1991:pasal-176"


def test_low_score_is_refused_without_calling_the_llm(retriever):
    provider = FakeProvider(ASK)
    out = _assistant(retriever, provider).ask("resep rendang padang yang enak sekali")
    assert out.response.status == "ditolak" and out.response.sumber == []
    assert provider.calls == []


def test_retrieval_only_without_provider(retriever):
    r = _assistant(retriever, None).ask(ASK_Q).response
    assert (r.status, r.mode) == ("ok", "retrieval_only")
    assert r.sumber[0].chunk_id == "khi-1991:pasal-176" and r.sitasi[0] == "khi-1991:pasal-176"


def test_provider_unavailable_falls_back_with_provider_failed(retriever):
    out = _assistant(retriever, FakeProvider(ProviderUnavailable("429"))).ask(ASK_Q)
    assert out.response.mode == "retrieval_only" and out.provider_failed


def test_provider_error_falls_back_without_provider_failed(retriever):
    out = _assistant(retriever, FakeProvider(ProviderError("bad json"))).ask(ASK_Q)
    assert out.response.mode == "retrieval_only" and not out.provider_failed


def test_out_of_scope_and_all_invalid_citations(retriever):
    out = _assistant(retriever, FakeProvider({"status": "di_luar_cakupan"})).ask(ASK_Q)
    assert out.response.status == "di_luar_cakupan" and out.response.sumber == []
    bad = {"status": "ok", "jawaban": "x", "sitasi": ["x:y"]}
    assert _assistant(retriever, FakeProvider(bad)).ask(ASK_Q).response.status == "ditolak"


def test_answer_from_hits_replays_cached_hits(chunks):
    a = Assistant({c.chunk_id: c for c in chunks}, FakeProvider(ASK), threshold=0.1)
    out = a.answer_from_hits("ask", ASK_Q, [Hit("khi-1991:pasal-176", 0.0, 0.9)])
    assert out.response.sitasi == ["khi-1991:pasal-176"] and out.top_score == 0.9


def test_prompt_contents(chunks):
    cmap = {c.chunk_id: c for c in chunks}
    msgs = messages("navigator", NAV_Q, context_block(["khi-1991:pasal-116"], cmap))
    assert msgs[0]["role"] == "system" and "JSON" in msgs[0]["content"]
    assert "[khi-1991:pasal-116] KHI Pasal 116" in msgs[1]["content"]
    assert NAV_Q in msgs[1]["content"] and "jenis_perkara" in msgs[0]["content"]
    assert "jenis_perkara" not in messages("ask", ASK_Q, "")[0]["content"]
    assert len(PROMPT_VERSION) == 12 and "Arab" in SYSTEM


def test_prompt_version_matches_file_hash():
    prompts_file = Path(__file__).parent.parent.parent / "app" / "generation" / "prompts.py"
    file_hash = hashlib.sha256(
        prompts_file.read_text(encoding="utf-8").replace("\r\n", "\n").encode("utf-8")
    ).hexdigest()[:12]
    assert PROMPT_VERSION == file_hash


def test_blank_answer_is_refused_with_draft_and_stats(retriever):
    blank = {"status": "ok", "jawaban": "  \n", "sitasi": ["khi-1991:pasal-176"]}
    out = _assistant(retriever, FakeProvider(blank)).ask(ASK_Q)
    assert (out.response.status, out.response.mode) == ("ditolak", "llm")
    assert out.draft["jawaban"] == "  \n" and out.stats.citations_valid == 1
