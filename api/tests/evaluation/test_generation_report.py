import asyncio
import json
import math
from types import SimpleNamespace

import httpx
import pytest

openai = pytest.importorskip("openai")  # ponytail: dep of ragas extra, absent in CI

from app.evaluation.generation_report import (
    _score_all,
    _sha,
    judge_label,
    markdown,
    ragas_todo,
    response_text,
    summarize,
    usable_scores,
)


def _row(key, in_domain, status, top, total=None, valid=None, kind="ask", set_="gold",
         mode="llm", text=None):
    return {"key": key, "qid": key.split(":")[1], "kind": kind, "set": set_,
            "in_domain": in_domain, "status": status,
            "mode": mode, "top_score": top, "citations_total": total, "citations_valid": valid,
            "steps_total": None, "steps_kept": None, "question": f"q {key}",
            "retrieved": ["khi-1991:pasal-116"],
            "response": {"jawaban": text or f"jawab {key}"}}


ROWS = [_row("ask:cerai-001", True, "ok", 0.8, 2, 1),
        _row("ask:cerai-002", True, "ditolak", 0.01),
        _row("ask:luar-001", False, "di_luar_cakupan", 0.5, None, None),
        _row("ask:luar-002", False, "ok", 0.2, 1, 1)]
SCORES = {"ask:cerai-001": {"faithfulness": 0.9, "answer_relevancy": 0.8},
          "ask:luar-002": {"faithfulness": 0.5, "answer_relevancy": 0.4}}
MD_META = {"provider": "groq", "model": "m", "judge_model": "j", "prompt_version": "p",
           "threshold": 0.0333, "ragas": "0.4.3", "date": "2026-10-07"}


def test_summarize():
    summary = summarize(ROWS, SCORES, threshold=0.0333)
    s = summary["ask/gold"]
    assert (s["n"], s["answered"], s["fallback"]) == (4, 2, 0)
    assert s["in_domain_refused"] == 0.5 and s["out_of_domain_refused"] == 0.5
    assert s["out_of_domain_below_threshold"] == 0.0
    assert s["citation_precision"] == round(2 / 3, 4)
    assert (s["faithfulness"], s["answer_relevancy"], s["n_scored"]) == (0.7, 0.6, 2)
    assert (s["n_nan"], s["n_error"]) == (0, 0)
    assert set(summary) == {"ask/gold"}


def test_summarize_with_fallback():
    rows = ROWS + [_row("ask:fallback-001", True, "ok", 0.8, None, None, mode="retrieval_only")]
    summary = summarize(rows, SCORES, threshold=0.0333)
    s = summary["ask/gold"]
    assert s["n"] == 5
    assert s["answered"] == 2
    assert s["fallback"] == 1


def test_response_text_and_todo(chunks):
    nav = {"kind": "navigator", "response": {
        "ringkasan": "R", "langkah": [{"urutan": 1, "judul": "J", "uraian": "U"}]}}
    assert response_text(nav) == "R\n1. J: U"
    cmap = {c.chunk_id: c for c in chunks}
    todo = ragas_todo(ROWS, cmap, done={"ask:luar-002"})
    assert [t[0] for t in todo] == ["ask:cerai-001"]
    _, _, response, contexts = todo[0]
    assert response == "jawab ask:cerai-001" and contexts[0].startswith("KHI Pasal 116\n")


def test_markdown_lists_groups_and_meta():
    md = markdown(summarize(ROWS, SCORES, 0.0333), MD_META)
    assert "| ask/gold | 4 | 2 | 0 |" in md and "0.700" in md and "judge model: `j`" in md


def test_markdown_has_new_columns_and_caveat():
    md = markdown(summarize(ROWS, SCORES, 0.0333), MD_META)
    assert "| n_scored | n_nan | n_error | inheritance_numbers_rate |" in md
    assert "inheritance_numbers_rate: share of answered kewarisan Q&A answers" in md


def test_summarize_ignores_nan_and_counts_nan_and_error_rows():
    scores = {**SCORES,
              "ask:cerai-002": {"faithfulness": None, "answer_relevancy": 0.5},
              "ask:luar-001": {"faithfulness": float("nan"), "answer_relevancy": 0.2},
              "ask:luar-002": {"faithfulness": None, "answer_relevancy": None,
                               "error": "ValueError"}}
    s = summarize(ROWS, scores, 0.0333)["ask/gold"]
    assert s["faithfulness"] == 0.9 and s["answer_relevancy"] == round((0.8 + 0.5 + 0.2) / 3, 4)
    assert (s["n_scored"], s["n_nan"], s["n_error"]) == (4, 2, 1)
    assert "NaN" not in json.dumps(s)


def test_inheritance_numbers_rate():
    rows = [_row("ask:waris-001", True, "ok", 0.8, 1, 1, text="Anak perempuan mendapat 1/2."),
            _row("ask:waris-002", True, "ok", 0.8, 1, 1, text="Ibu mendapat Sepertiga bagian."),
            _row("ask:waris-003", True, "ok", 0.8, 1, 1, text="Ahli waris ditentukan hakim."),
            _row("ask:waris-004", True, "ditolak", 0.8, text="1/2"),  # not answered: skipped
            _row("ask:cerai-001", True, "ok", 0.8, 1, 1, text="bagian 1/2")]  # not kewarisan
    assert summarize(rows, {}, 0.1)["ask/gold"]["inheritance_numbers_rate"] == round(2 / 3, 4)
    assert summarize(ROWS, {}, 0.1)["ask/gold"]["inheritance_numbers_rate"] is None


META = {"model": "m", "prompt_version": "p"}


def _score(key, text, **over):
    return {"key": key, "faithfulness": 1.0, "answer_relevancy": 1.0, "judge": "j",
            "model": "m", "prompt_version": "p", "response_sha": _sha(text), **over}


def test_usable_scores_requires_all_four_to_match():
    rows = [_row("ask:a-1", True, "ok", 0.8, 1, 1)]
    text = "jawab ask:a-1"
    good = _score("ask:a-1", text)
    for stale in ({"judge": "other"}, {"model": "x"}, {"prompt_version": "y"},
                  {"response_sha": "0" * 16}):
        assert usable_scores(rows, [_score("ask:a-1", text, **stale)], META, "j") == {}
    assert usable_scores(rows, [{"key": "ask:a-1", "faithfulness": 1.0}], META, "j") == {}
    assert usable_scores(rows, [_score("ask:a-1", text, judge="other"), good], META,
                         "j") == {"ask:a-1": good}
    # --skip-ragas: no judge needed to match, the judge is read from the score rows
    other = _score("ask:a-1", text, judge="other")
    assert usable_scores(rows, [other], META, None) == {"ask:a-1": other}
    assert judge_label({"a": other, "b": good}, "env") == "j, other"
    assert judge_label({"b": good}, "env") == "j"
    assert judge_label({}, "env") == "env (no scores)"


class _Metric:
    def __init__(self, behaviour):
        self.behaviour = behaviour

    async def ascore(self, **kwargs):
        if isinstance(self.behaviour, Exception):
            raise self.behaviour
        return SimpleNamespace(value=self.behaviour)


def _drive(todo, faithfulness, relevancy, path):
    prov = {"judge": "j", "model": "m", "prompt_version": "p"}
    asyncio.run(_score_all(todo, faithfulness, relevancy, path, 0.0, prov))
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


TODO = [("ask:a-1", "q", "resp", ["ctx"]), ("ask:a-2", "q", "resp2", ["ctx"])]


def test_score_all_nan_is_stored_as_null_with_provenance(tmp_path):
    rows = _drive(TODO, _Metric(float("nan")), _Metric(0.5), tmp_path / "s.jsonl")
    assert "NaN" not in (tmp_path / "s.jsonl").read_text(encoding="utf-8")
    assert rows[0] == {"key": "ask:a-1", "faithfulness": None, "answer_relevancy": 0.5,
                       "judge": "j", "model": "m", "prompt_version": "p",
                       "response_sha": _sha("resp")}
    assert math.isfinite(rows[1]["answer_relevancy"])


def test_score_all_non_transient_error_row_and_continues(tmp_path):
    rows = _drive(TODO, _Metric(ValueError("empty response")), _Metric(0.5),
                  tmp_path / "s.jsonl")
    assert [r["error"] for r in rows] == ["ValueError", "ValueError"]
    assert rows[0]["faithfulness"] is None and rows[0]["answer_relevancy"] is None
    assert [r["key"] for r in rows] == ["ask:a-1", "ask:a-2"]


def test_score_all_transient_error_stops_the_run(tmp_path):
    request = httpx.Request("POST", "http://judge")
    limit = openai.RateLimitError("429", response=httpx.Response(429, request=request),
                                  body=None)
    path = tmp_path / "s.jsonl"
    seen = []

    class Flaky:
        async def ascore(self, **kwargs):
            seen.append(1)
            if len(seen) > 1:
                raise limit
            return SimpleNamespace(value=0.7)

    with pytest.raises(openai.RateLimitError):
        _drive(TODO, Flaky(), _Metric(0.5), path)
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [r["key"] for r in rows] == ["ask:a-1"]  # first sample kept, second not recorded
    wrapped = RuntimeError("retries exhausted")
    wrapped.__cause__ = openai.APIConnectionError(request=request)
    with pytest.raises(RuntimeError):
        _drive(TODO[:1], _Metric(wrapped), _Metric(0.5), tmp_path / "w.jsonl")
    assert not (tmp_path / "w.jsonl").exists()
