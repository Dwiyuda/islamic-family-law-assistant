import json

import pytest

from app.evaluation.generation import Case, build_cases, collect_hits, generate
from app.evaluation.gold import GoldItem
from app.generation.fakes import FakeProvider
from app.generation.providers import ProviderError, ProviderUnavailable
from app.generation.service import NAVIGATOR_DOMAINS, Assistant

META = {"provider": "fake", "model": "fake", "prompt_version": "x", "threshold": 0.1}
ASK = {"status": "ok", "jawaban": "Separoh.", "sitasi": ["khi-1991:pasal-176"]}
CASES = [Case("ask", "waris-101", "berapa bagian anak perempuan", True, "heldout"),
         Case("ask", "luar-101", "cara membuat paspor baru", False, "heldout")]
HITS = {"ask:waris-101": [["khi-1991:pasal-176", 0.9]],
        "ask:luar-101": [["uu-7-1989:pasal-49", 0.01]]}


def _gold(qid, question, topic, ids):
    return GoldItem(qid=qid, question=question, topic=topic, relevant_chunk_ids=ids)


class _SwitchableProvider:
    """Provider that can switch between success and failure modes."""
    def __init__(self, success_reply, fail_after=None):
        self.name, self.model = "fake", "fake"
        self.success_reply = success_reply
        self.fail_after = fail_after
        self.call_count = 0

    def complete(self, messages, schema):
        self.call_count += 1
        if self.fail_after is not None and self.call_count > self.fail_after:
            raise ProviderUnavailable("simulated failure")
        return self.success_reply


def test_build_cases():
    gold = [_gold("cerai-001", "Apakah saya bisa cerai?", "perceraian", ["khi-1991:pasal-116"]),
            _gold("luar-001", "Bagaimana cara bayar pajak?", "luar_domain", [])]
    held = [_gold("waris-101", "Berapa bagian ibu saya?", "kewarisan", ["khi-1991:pasal-178"])]
    cases = build_cases(gold, held)
    assert [c.key for c in cases] == ["ask:cerai-001", "ask:luar-001", "ask:waris-101",
                                      "navigator:cerai-001"]
    assert [c.set for c in cases] == ["gold", "gold", "heldout", "gold"]


def test_collect_hits_caches_and_resumes(tmp_path, retriever):
    calls = []

    def search(question, **kwargs):
        calls.append(kwargs.get("domains"))
        return retriever.search(question, **kwargs)

    cases = [Case("ask", "cerai-001", "Suami melanggar taklik talak", True, "gold"),
             Case("navigator", "cerai-001", "Suami melanggar taklik talak", True, "gold")]
    path = tmp_path / "hits.json"
    hits = collect_hits(cases, search, path)
    assert hits["ask:cerai-001"][0][0] == "khi-1991:pasal-116"
    assert calls == [None, NAVIGATOR_DOMAINS]
    assert collect_hits(cases, search, path) == hits and len(calls) == 2


def test_collect_hits_partial_cache_resumes(tmp_path, retriever):
    """Test that partial cache only searches missing keys."""
    calls = []

    def search(question, **kwargs):
        calls.append(question)
        return retriever.search(question, **kwargs)

    cases = [Case("ask", "cerai-001", "Q1", True, "gold"),
             Case("ask", "cerai-002", "Q2", True, "gold")]
    path = tmp_path / "hits.json"
    hits = collect_hits(cases[:1], search, path)
    assert "ask:cerai-001" in hits and len(calls) == 1
    calls.clear()
    hits = collect_hits(cases, search, path)
    assert len(calls) == 1 and calls[0] == "Q2"  # Only searched for missing case


def test_generate_writes_rows_resumes_and_checks_meta(tmp_path, chunks):
    a = Assistant({c.chunk_id: c for c in chunks}, FakeProvider(ASK), threshold=0.1)
    out, meta = tmp_path / "gen.jsonl", tmp_path / "meta.json"
    assert generate(CASES, HITS, a, out, meta, META) == 2
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert [(r["key"], r["status"]) for r in rows] == [("ask:waris-101", "ok"),
                                                      ("ask:luar-101", "ditolak")]
    assert rows[0]["citations_valid"] == 1 and rows[1]["citations_total"] is None
    assert rows[0]["retrieved"] == ["khi-1991:pasal-176"] and rows[0]["set"] == "heldout"
    assert generate(CASES, HITS, a, out, meta, META) == 0
    with pytest.raises(SystemExit) as exc_info:
        generate(CASES, HITS, a, out, meta, {**META, "model": "other"})
    assert "ragas_scores.jsonl" in str(exc_info.value)
    assert "generation_hits.json" not in str(exc_info.value)


def test_generate_mid_run_resume_on_unavailable(tmp_path, chunks):
    """Test resume after provider becomes unavailable mid-run."""
    provider = _SwitchableProvider(ASK, fail_after=1)
    a = Assistant({c.chunk_id: c for c in chunks}, provider, threshold=0.1)
    out, meta = tmp_path / "gen.jsonl", tmp_path / "meta.json"
    hits = {"ask:waris-101": [["khi-1991:pasal-176", 0.9]],
            "ask:luar-101": [["uu-7-1989:pasal-49", 0.5]]}
    with pytest.raises(SystemExit) as exc_info:
        generate(CASES, hits, a, out, meta, META)
    assert "1 rows" in str(exc_info.value)
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 1 and rows[0]["key"] == "ask:waris-101"
    provider.fail_after = None
    assert generate(CASES, hits, a, out, meta, META) == 1
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 2


def test_generate_truncated_jsonl_line_is_dropped(tmp_path, chunks):
    """Test that truncated last JSONL line is dropped and run resumes."""
    a = Assistant({c.chunk_id: c for c in chunks}, FakeProvider(ASK), threshold=0.1)
    out, meta = tmp_path / "gen.jsonl", tmp_path / "meta.json"
    generate(CASES, HITS, a, out, meta, META)
    content = out.read_text(encoding="utf-8")
    out.write_text(content + '{"incomplete', encoding="utf-8")
    assert generate(CASES, HITS, a, out, meta, META) == 0
    lines = [l for l in out.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(lines) == 2


def test_generate_rows_present_meta_missing_exits(tmp_path, chunks):
    """Test that rows without meta file causes SystemExit."""
    a = Assistant({c.chunk_id: c for c in chunks}, FakeProvider(ASK), threshold=0.1)
    out, meta = tmp_path / "gen.jsonl", tmp_path / "meta.json"
    out.write_text('{"key": "ask:test"}\n', encoding="utf-8")
    with pytest.raises(SystemExit) as exc_info:
        generate(CASES, HITS, a, out, meta, META)
    msg = str(exc_info.value)
    assert "generation_meta.json" in msg and "ragas_scores.jsonl" in msg
    assert "generation_hits.json" not in msg


def test_generate_stops_on_provider_unavailable_and_missing_hits(tmp_path, chunks):
    a = Assistant({c.chunk_id: c for c in chunks},
                  FakeProvider(ProviderUnavailable("429")), threshold=0.1)
    out, meta = tmp_path / "gen.jsonl", tmp_path / "meta.json"
    with pytest.raises(SystemExit):
        generate(CASES[:1], HITS, a, out, meta, META)
    assert not out.exists() or out.read_text(encoding="utf-8") == ""
    with pytest.raises(SystemExit):
        generate(CASES, {}, a, out, meta, META)


def test_generate_plain_provider_error_writes_retrieval_only_row(tmp_path, chunks):
    """Test that plain ProviderError (bad JSON) doesn't stop run, writes retrieval_only."""
    a = Assistant({c.chunk_id: c for c in chunks}, FakeProvider(ProviderError("bad json")),
                  threshold=0.1)
    out, meta = tmp_path / "gen.jsonl", tmp_path / "meta.json"
    assert generate(CASES, HITS, a, out, meta, META) == 2
    rows = [json.loads(line) for line in out.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["mode"] == "retrieval_only" and rows[0]["status"] == "ok"
