"""Generation evaluation (spec 8.2), in two stages:

`hits`: hybrid_rerank top-8 per case, cached (CPU reranker ~45 s/case; run it detached).
`generate`: replays the cached hits through the Assistant + LLM, one JSONL row per case,
resumable across free-tier rate-limit days."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

from app.config import DEFAULT_DEVICE, REFUSAL_THRESHOLD, TOP_K, load_env_file
from app.generation.prompts import PROMPT_VERSION
from app.generation.providers import make_provider
from app.generation.service import NAVIGATOR_DOMAINS, Assistant
from app.retrieval.corpus import REPO_ROOT, load_corpus
from app.retrieval.retriever import Hit

from .gold import GOLD_PATH, GoldItem, load_gold
from .jsonl_io import read_jsonl_rows

HELDOUT_PATH = REPO_ROOT / "eval" / "heldout.jsonl"
RESULTS = REPO_ROOT / "eval" / "results"
STAT_KEYS = ("citations_total", "citations_valid", "steps_total", "steps_kept")


@dataclass(frozen=True)
class Case:
    kind: str  # "ask" | "navigator"
    qid: str
    question: str
    in_domain: bool
    set: str  # "gold" | "heldout"

    @property
    def key(self) -> str:
        return f"{self.kind}:{self.qid}"


def build_cases(gold: list[GoldItem], heldout: list[GoldItem]) -> list[Case]:
    cases = [Case("ask", g.qid, g.question, g.in_domain, "gold") for g in gold]
    cases += [Case("ask", g.qid, g.question, g.in_domain, "heldout") for g in heldout]
    cases += [Case("navigator", g.qid, g.question, True, "gold")
              for g in gold if g.topic == "perceraian"]
    return cases


def collect_hits(cases: list[Case], search: Callable[..., list[Hit]], cache_path: Path,
                 progress: Callable[[str, int, int], None] | None = None
                 ) -> dict[str, list]:
    cache = (json.loads(cache_path.read_text(encoding="utf-8"))
             if cache_path.exists() else {})
    todo = [c for c in cases if c.key not in cache]
    for i, case in enumerate(todo, start=1):
        domains = NAVIGATOR_DOMAINS if case.kind == "navigator" else None
        hits = search(case.question, top_k=TOP_K, method="hybrid_rerank", domains=domains)
        cache[case.key] = [[h.chunk_id, h.rerank_score] for h in hits]
        tmp_path = cache_path.with_name(cache_path.name + ".tmp")
        tmp_path.write_text(json.dumps(cache, ensure_ascii=False, indent=0),
                            encoding="utf-8")
        os.replace(str(tmp_path), str(cache_path))
        if progress:
            progress(case.key, i, len(todo))
    return cache


def generate(cases: list[Case], hits: dict[str, list], assistant: Assistant, out_path: Path,
             meta_path: Path, meta: dict) -> int:
    missing = [c.key for c in cases if c.key not in hits]
    if missing:
        raise SystemExit(f"{len(missing)} cases have no cached hits; run --stage hits first")
    if out_path.exists() and out_path.stat().st_size > 0 and not meta_path.exists():
        raise SystemExit(
            "existing rows in eval/results/generation.jsonl but no "
            "eval/results/generation_meta.json; move eval/results/generation.jsonl, "
            "eval/results/generation_meta.json and eval/results/ragas_scores.jsonl away to "
            "start a new run")
    if meta_path.exists() and json.loads(meta_path.read_text(encoding="utf-8")) != meta:
        raise SystemExit(
            "existing rows came from a different provider/model/prompt/threshold; "
            "move eval/results/generation.jsonl, eval/results/generation_meta.json and "
            "eval/results/ragas_scores.jsonl away to start a new run")
    meta_path.write_text(json.dumps(meta, indent=1), encoding="utf-8")
    done = {row["key"] for row in read_jsonl_rows(out_path)}
    written = 0
    for case in cases:
        if case.key in done:
            continue
        cached = [Hit(cid, 0.0, score) for cid, score in hits[case.key]]
        outcome = assistant.answer_from_hits(case.kind, case.question, cached)
        if outcome.provider_failed:
            raise SystemExit(f"LLM provider failed at {case.key} after retries; {written} rows"
                             " written this run. Re-run later to resume.")
        stats = asdict(outcome.stats) if outcome.stats else dict.fromkeys(STAT_KEYS)
        row = {"key": case.key, "kind": case.kind, "qid": case.qid, "set": case.set,
               "in_domain": case.in_domain, "question": case.question,
               "top_score": outcome.top_score, "status": outcome.response.status,
               "mode": outcome.response.mode, "retrieved": outcome.retrieved,
               "draft": outcome.draft, "response": outcome.response.model_dump(), **stats}
        with out_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        written += 1
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Generation evaluation (cached hits + LLM)")
    parser.add_argument("--stage", choices=("hits", "generate"), required=True)
    parser.add_argument("--device", default=DEFAULT_DEVICE)
    parser.add_argument("--threads", type=int, default=0)
    args = parser.parse_args()
    cases = build_cases(load_gold(GOLD_PATH), load_gold(HELDOUT_PATH))
    RESULTS.mkdir(parents=True, exist_ok=True)
    hits_path = RESULTS / "generation_hits.json"
    if args.stage == "hits":
        if args.threads > 0:
            import torch

            torch.set_num_threads(args.threads)
        from app.retrieval.indexer import open_retriever
        from app.retrieval.models import BGEM3Embedder, BGEReranker

        retriever = open_retriever(REPO_ROOT / "data", REPO_ROOT / "data" / "qdrant",
                                   BGEM3Embedder(device=args.device),
                                   BGEReranker(device=args.device))
        try:
            collect_hits(cases, retriever.search, hits_path,
                         progress=lambda key, i, n: print(f"{key} {i}/{n}", file=sys.stderr))
        finally:
            retriever.store.close()
        return
    load_env_file(REPO_ROOT / ".env")
    provider = make_provider()
    if provider is None:
        raise SystemExit("set LLM_PROVIDER, LLM_MODEL and the provider's API key in .env")
    chunks = {c.chunk_id: c for c in load_corpus(REPO_ROOT / "data")}
    meta = {"provider": provider.name, "model": provider.model,
            "prompt_version": PROMPT_VERSION, "threshold": REFUSAL_THRESHOLD}
    written = generate(cases, json.loads(hits_path.read_text(encoding="utf-8")),
                       Assistant(chunks, provider), RESULTS / "generation.jsonl",
                       RESULTS / "generation_meta.json", meta)
    print(f"{written} rows written")
    fallbacks = sum(r["mode"] == "retrieval_only"
                    for r in read_jsonl_rows(RESULTS / "generation.jsonl"))
    print(f"{fallbacks} fallback rows (LLM answer unusable); "
          "many fallbacks usually mean a wrong LLM_MODEL")


if __name__ == "__main__":
    main()
