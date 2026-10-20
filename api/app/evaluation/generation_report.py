"""RAGAS scoring (faithfulness, answer relevancy) of generation rows, and the report.

Scores are appended to eval/results/ragas_scores.jsonl one sample at a time, so a judge
rate-limit stop loses nothing; re-run to resume. Every score line carries its provenance (judge,
model, prompt version, response hash) so scores of an older generation are never reused.
ragas/openai/FlagEmbedding are imported only inside _ragas_metrics so unit tests never need
them."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import math
import os
import re
import sys
from datetime import date
from pathlib import Path

from app.config import load_env_file
from app.ingest.models import Chunk
from app.retrieval.corpus import REPO_ROOT, index_text, load_corpus

from .jsonl_io import read_jsonl_rows

RESULTS = REPO_ROOT / "eval" / "results"
GROUPS = [(kind, set_) for kind in ("ask", "navigator") for set_ in ("gold", "heldout")]
# spec 2.3: inheritance amounts belong to the faraid engine (Fase 4); this measures how often
# a kewarisan answer states shares/fractions anyway.
INHERITANCE_NUMBERS = re.compile(
    r"\d+\s*/\s*\d+|seper(dua|tiga|empat|enam|delapan)|separ(uh|oh)|dua pertiga|sepertiga",
    re.IGNORECASE)


def response_text(row: dict) -> str:
    r = row["response"]
    if row["kind"] == "ask":
        return r["jawaban"]
    steps = "\n".join(f"{s['urutan']}. {s['judul']}: {s['uraian']}" for s in r["langkah"])
    return f"{r['ringkasan']}\n{steps}".strip()


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def usable_scores(rows: list[dict], score_rows: list[dict], meta: dict,
                  judge: str | None) -> dict[str, dict]:
    """Score lines belonging to the current generation: same model, prompt version and
    response text (and judge, unless None). Other lines stay in the file but are ignored."""
    by_key = {r["key"]: r for r in rows}
    return {s["key"]: s for s in score_rows
            if s["key"] in by_key and s.get("model") == meta["model"]
            and s.get("prompt_version") == meta["prompt_version"]
            and s.get("response_sha") == _sha(response_text(by_key[s["key"]]))
            and (judge is None or s.get("judge") == judge)}


def judge_label(scores: dict[str, dict], env_judge: str | None) -> str:
    judges = sorted({s["judge"] for s in scores.values()})
    return ", ".join(judges) if judges else f"{env_judge or '-'} (no scores)"


def ragas_todo(rows: list[dict], chunks: dict[str, Chunk],
               done: set[str]) -> list[tuple[str, str, str, list[str]]]:
    return [(r["key"], r["question"], response_text(r),
             [index_text(chunks[cid]) for cid in r["retrieved"]])
            for r in rows if r["status"] == "ok" and r["mode"] == "llm" and r["key"] not in done]


def _finite(value) -> bool:
    return value is not None and math.isfinite(value)


def _mean(values: list[float | None]) -> float | None:
    values = [v for v in values if _finite(v)]
    return round(sum(values) / len(values), 4) if values else None


def _rate(rows: list[dict], pred) -> float | None:
    return round(sum(1 for r in rows if pred(r)) / len(rows), 4) if rows else None


def summarize(rows: list[dict], scores: dict[str, dict], threshold: float) -> dict:
    summary = {}
    for kind, set_ in GROUPS:
        group = [r for r in rows if r["kind"] == kind and r["set"] == set_]
        if not group:
            continue
        inside = [r for r in group if r["in_domain"]]
        outside = [r for r in group if not r["in_domain"]]
        drafted = [r for r in group if r["citations_total"] is not None]
        total = sum(r["citations_total"] for r in drafted)
        scored = [scores[r["key"]] for r in group if r["key"] in scores]
        waris = [r for r in group if r["status"] == "ok" and r["mode"] == "llm"
                 and r.get("qid", "").startswith("waris-")]
        summary[f"{kind}/{set_}"] = {
            "n": len(group),
            "answered": sum(r["status"] == "ok" and r["mode"] == "llm" for r in group),
            "fallback": sum(r["mode"] == "retrieval_only" and r["status"] == "ok" for r in group),
            "in_domain_refused": _rate(inside, lambda r: r["status"] != "ok"),
            "out_of_domain_refused": _rate(outside, lambda r: r["status"] != "ok"),
            "out_of_domain_below_threshold": _rate(outside, lambda r: r["top_score"] < threshold),
            "citation_precision": (round(sum(r["citations_valid"] for r in drafted) / total, 4)
                                   if total else None),
            "steps_kept": (f"{sum(r['steps_kept'] or 0 for r in drafted)}/"
                           f"{sum(r['steps_total'] or 0 for r in drafted)}"
                           if kind == "navigator" else None),
            "faithfulness": _mean([s["faithfulness"] for s in scored]),
            "answer_relevancy": _mean([s["answer_relevancy"] for s in scored]),
            "n_scored": len(scored),
            # error rows (judge failed) are counted in n_error only, not as NaN
            "n_nan": sum(1 for s in scored if not s.get("error") and not (
                _finite(s["faithfulness"]) and _finite(s["answer_relevancy"]))),
            "n_error": sum(1 for s in scored if s.get("error")),
            "inheritance_numbers_rate": _rate(
                waris, lambda r: INHERITANCE_NUMBERS.search(response_text(r))),
        }
    return summary


def _fmt(value) -> str:
    if value is None:
        return "—"
    return f"{value:.3f}" if isinstance(value, float) else str(value)


def markdown(summary: dict, meta: dict) -> str:
    cols = ["n", "answered", "fallback", "in_domain_refused", "out_of_domain_refused",
            "out_of_domain_below_threshold", "citation_precision", "steps_kept",
            "faithfulness", "answer_relevancy", "n_scored", "n_nan", "n_error",
            "inheritance_numbers_rate"]
    lines = ["# Generation evaluation", "",
             "| Group | " + " | ".join(cols) + " |", "|---" * (len(cols) + 1) + "|"]
    for group, row in summary.items():
        lines.append(f"| {group} | " + " | ".join(_fmt(row[c]) for c in cols) + " |")
    lines += [
        "",
        ("Targets (spec 8.2): faithfulness ≥ 0.85; out-of-domain refused ≥ 90%; "
         "in-domain wrongly refused ≤ 10%."),
        "",
        ("- `gold` rows reuse the threshold fitted on the same 100 gold questions (in-sample); "
         "`heldout` rows are out-of-sample (eval/heldout.jsonl, never used for fitting)."),
        ("- Faithfulness and answer relevancy are LLM-judged (RAGAS prompts are English, answers "
         "Indonesian); treat small differences as noise. If the judge model equals the "
         "generator, the judge grades its own model family."),
        ("- `out_of_domain_below_threshold`: refused by the retrieval threshold alone, before "
         "the LLM."),
        ("- `n_nan`: scored rows whose RAGAS metric is NaN (no statements extracted); "
         "`n_error`: rows the judge failed on for a non-transient reason. Both are left out of "
         "the means."),
        ("- inheritance_numbers_rate: share of answered kewarisan Q&A answers that state "
         "shares/fractions; spec 2.3 says amounts come from the faraid engine (Fase 4), so "
         "this is tracked as a known risk."),
        "",
        "## Run configuration",
        "",
        f"- provider: `{meta['provider']}`, model: `{meta['model']}`, judge model: `{meta['judge_model']}`",
        f"- prompt version: `{meta['prompt_version']}`, REFUSAL_THRESHOLD: {meta['threshold']}",
        f"- ragas: {meta['ragas']}, date: {meta['date']}",
    ]
    return "\n".join(lines) + "\n"


def _ragas_metrics():
    from openai import AsyncOpenAI
    from ragas.embeddings.base import BaseRagasEmbedding
    from ragas.llms import llm_factory
    from ragas.metrics.collections import AnswerRelevancy, Faithfulness

    from app.generation.providers import BASE_URLS, KEY_VARS
    from app.retrieval.models import BGEM3Embedder

    provider = os.environ["LLM_PROVIDER"]
    judge = os.environ.get("JUDGE_MODEL") or os.environ["LLM_MODEL"]
    embedder = BGEM3Embedder()

    class BGEM3Embedding(BaseRagasEmbedding):
        def embed_text(self, text: str, **kwargs) -> list[float]:
            return embedder.encode([text])[0].dense

        async def aembed_text(self, text: str, **kwargs) -> list[float]:
            return self.embed_text(text)

    client = AsyncOpenAI(api_key=os.environ[KEY_VARS[provider]], base_url=BASE_URLS[provider],
                         max_retries=6)
    llm = llm_factory(judge, provider="openai", client=client, adapter="instructor")
    return judge, Faithfulness(llm=llm), AnswerRelevancy(llm=llm, embeddings=BGEM3Embedding())


def _num(value) -> float | None:
    """Non-finite RAGAS values (NaN) are stored as null so the JSON stays valid."""
    return float(value) if _finite(value) else None


def _chain(exc: BaseException | None):
    while exc is not None:
        yield exc
        exc = exc.__cause__ or exc.__context__


async def _score_all(todo, faithfulness, relevancy, out_path: Path, pause: float,
                     provenance: dict) -> None:
    """Score one sample at a time, appending each result. A transient judge failure (rate
    limit, connection, timeout, 5xx) stops the run so a re-run resumes; any other failure is
    recorded as an error row so one bad sample never blocks the rest."""
    import openai

    transient = (openai.RateLimitError, openai.APIConnectionError, openai.APITimeoutError,
                 openai.InternalServerError)
    for i, (key, question, response, contexts) in enumerate(todo, start=1):
        try:
            f = await faithfulness.ascore(user_input=question, response=response,
                                          retrieved_contexts=contexts)
            r = await relevancy.ascore(user_input=question, response=response)
            result = {"faithfulness": _num(f.value), "answer_relevancy": _num(r.value)}
        except Exception as exc:
            if any(isinstance(e, transient) for e in _chain(exc)):  # instructor may wrap
                raise
            result = {"faithfulness": None, "answer_relevancy": None,
                      "error": type(exc).__name__}
        with out_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"key": key, **result, **provenance,
                                 "response_sha": _sha(response)}) + "\n")
        print(f"{key} {i}/{len(todo)}", file=sys.stderr)
        await asyncio.sleep(pause)  # ponytail: fixed spacing keeps the free tier's RPM happy


def main() -> None:
    parser = argparse.ArgumentParser(description="RAGAS scoring + generation report")
    parser.add_argument("--pause", type=float, default=10.0)
    parser.add_argument("--skip-ragas", action="store_true")
    args = parser.parse_args()
    load_env_file(REPO_ROOT / ".env")
    rows = read_jsonl_rows(RESULTS / "generation.jsonl")
    meta = json.loads((RESULTS / "generation_meta.json").read_text(encoding="utf-8"))
    scores_path = RESULTS / "ragas_scores.jsonl"
    env_judge = os.environ.get("JUDGE_MODEL") or os.environ.get("LLM_MODEL")
    match_judge = None  # --skip-ragas: take the judge from the matching score rows
    if not args.skip_ragas:
        if not env_judge:
            raise SystemExit("set JUDGE_MODEL or LLM_MODEL (and the provider's API key) in "
                             ".env, or pass --skip-ragas")
        match_judge = env_judge
        chunks = {c.chunk_id: c for c in load_corpus(REPO_ROOT / "data")}
        done = set(usable_scores(rows, read_jsonl_rows(scores_path), meta, match_judge))
        todo = ragas_todo(rows, chunks, done)
        if todo:
            _, faithfulness, relevancy = _ragas_metrics()
            asyncio.run(_score_all(todo, faithfulness, relevancy, scores_path, args.pause,
                                   {"judge": env_judge, "model": meta["model"],
                                    "prompt_version": meta["prompt_version"]}))
    scores = usable_scores(rows, read_jsonl_rows(scores_path), meta, match_judge)
    summary = summarize(rows, scores, meta["threshold"])
    try:
        ragas_version = importlib.metadata.version("ragas")
    except importlib.metadata.PackageNotFoundError:
        ragas_version = "not installed"
    full_meta = {**meta, "judge_model": judge_label(scores, env_judge), "ragas": ragas_version,
                 "date": date.today().isoformat()}
    (RESULTS / "generation.json").write_text(
        json.dumps({"summary": summary, "meta": full_meta}, ensure_ascii=False, indent=1,
                   allow_nan=False),
        encoding="utf-8")
    (RESULTS / "generation.md").write_text(markdown(summary, full_meta), encoding="utf-8")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
