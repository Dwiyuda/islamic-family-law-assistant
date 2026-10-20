from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import sys
from collections.abc import Callable
from datetime import date
from pathlib import Path

from app.config import DEFAULT_DEVICE, RERANK_CANDIDATES, TOP_K
from app.retrieval.corpus import REPO_ROOT
from app.retrieval.retriever import METHODS, Retriever

from .gold import GOLD_PATH, GoldItem, load_gold
from .metrics import mrr_at_k, ndcg_at_k, recall_at_k

METRICS = ("recall@5", "mrr@10", "ndcg@10")
LIBRARIES = ("FlagEmbedding", "torch", "qdrant-client", "rank-bm25")


def evaluate(retriever: Retriever, gold: list[GoldItem], methods=METHODS, depth: int = 10,
             progress: Callable[[str, int, int], None] | None = None) -> dict:
    results: dict = {"methods": {}}
    in_domain = [g for g in gold if g.in_domain]
    # Controller ruling: reuse the hybrid_rerank per-question search below for rerank_top
    # instead of re-searching every in-domain question a second time (CPU reranking is slow).
    hybrid_rerank_hits: dict[str, list] = {}
    for method in methods:
        rows = []
        for i, g in enumerate(in_domain, start=1):
            hits = retriever.search(g.question, top_k=depth, method=method)
            if method == "hybrid_rerank":
                hybrid_rerank_hits[g.qid] = hits
            ranked = [h.chunk_id for h in hits]
            relevant = set(g.relevant_chunk_ids)
            rows.append({"qid": g.qid, "recall@5": recall_at_k(ranked, relevant, 5),
                         "mrr@10": mrr_at_k(ranked, relevant, 10),
                         "ndcg@10": ndcg_at_k(ranked, relevant, 10), "top10": ranked[:10]})
            if progress:
                progress(method, i, len(in_domain))
        results["methods"][method] = {
            "n": len(rows),
            **{m: round(sum(r[m] for r in rows) / len(rows), 4) for m in METRICS},
            "per_question": rows,
        }
    if "hybrid_rerank" in methods:
        rerank_top = []
        for g in gold:
            if g.in_domain:
                hits = hybrid_rerank_hits.get(g.qid, [])
            else:
                hits = retriever.search(g.question, top_k=1, method="hybrid_rerank")
            score = (hits[0].rerank_score or 0.0) if hits else 0.0
            rerank_top.append({"qid": g.qid, "in_domain": g.in_domain, "score": score})
        results["rerank_top"] = rerank_top
    return results


def run_configuration_section(device: str | None, threads: int, chunks_path: Path,
                              reranker_max_length: int = 512,
                              versions: dict[str, str] | None = None,
                              today: str | None = None) -> str:
    """Records what actually produced the published numbers, for reproducibility.

    `versions` and `today` are injectable so the unit test can use fakes instead of
    reading real installed packages / the real clock.
    """
    if versions is None:
        versions = {name: importlib.metadata.version(name) for name in LIBRARIES}
    today = today or date.today().isoformat()
    digest = hashlib.sha256(chunks_path.read_bytes()).hexdigest()
    lines = [
        "## Run configuration", "",
        f"- device: `{device}`, threads: {threads}",
        f"- reranker max_length: {reranker_max_length}",
        f"- RERANK_CANDIDATES: {RERANK_CANDIDATES}, TOP_K: {TOP_K}",
        "- library versions: " + ", ".join(f"{k} {v}" for k, v in versions.items()),
        f"- chunks.jsonl sha256: `{digest}`",
        f"- date: {today}",
    ]
    return "\n".join(lines) + "\n"


def markdown_table(results: dict) -> str:
    lines = ["| Method | Recall@5 | MRR@10 | nDCG@10 |", "|---|---|---|---|"]
    for method, row in results["methods"].items():
        lines.append(f"| {method} | {row['recall@5']:.3f} | {row['mrr@10']:.3f} | "
                     f"{row['ndcg@10']:.3f} |")
    return "\n".join(lines)


def main() -> None:
    import inspect

    from app.retrieval.indexer import open_retriever
    from app.retrieval.models import BGEM3Embedder, BGEReranker

    parser = argparse.ArgumentParser(description="Retrieval evaluation on eval/gold.jsonl")
    parser.add_argument("--data-dir", type=Path, default=REPO_ROOT / "data")
    parser.add_argument("--qdrant-path", type=Path, default=REPO_ROOT / "data" / "qdrant")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "eval" / "results")
    parser.add_argument("--device", default=DEFAULT_DEVICE,
                        help="e.g. 'cpu' or 'cuda:0'; defaults to IFLA_DEVICE env var or 'cpu'")
    parser.add_argument("--threads", type=int, default=0,
                        help="torch.set_num_threads; 0 = leave torch's default")
    args = parser.parse_args()
    if args.threads > 0:
        import torch

        torch.set_num_threads(args.threads)
    retriever = open_retriever(args.data_dir, args.qdrant_path,
                               BGEM3Embedder(device=args.device),
                               BGEReranker(device=args.device))

    def progress(method: str, i: int, n: int) -> None:
        print(f"{method} {i}/{n}", file=sys.stderr)

    try:
        results = evaluate(retriever, load_gold(GOLD_PATH), progress=progress)
    finally:
        retriever.store.close()
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "retrieval.json").write_text(json.dumps(results, ensure_ascii=False, indent=1),
                                             encoding="utf-8")
    table = markdown_table(results)
    reranker_max_length = inspect.signature(BGEReranker.__init__).parameters["max_length"].default
    config_section = run_configuration_section(
        args.device, args.threads, args.data_dir / "processed" / "chunks.jsonl",
        reranker_max_length=reranker_max_length)
    (args.out / "retrieval.md").write_text(
        f"# Retrieval evaluation\n\n80 in-domain questions from `eval/gold.jsonl`.\n\n"
        f"{table}\n\n{config_section}",
        encoding="utf-8")
    print(table)


if __name__ == "__main__":
    main()
