from __future__ import annotations

import itertools
import json
from dataclasses import asdict, dataclass

from app.retrieval.corpus import REPO_ROOT


@dataclass(frozen=True)
class ThresholdChoice:
    threshold: float
    refusal_accuracy: float  # share of out-of-domain questions refused
    false_refusal_rate: float  # share of in-domain questions refused


def choose_threshold(in_scores: list[float], out_scores: list[float]) -> ThresholdChoice:
    distinct = sorted(set(in_scores) | set(out_scores))
    candidates = [0.0] + [(a + b) / 2 for a, b in itertools.pairwise(distinct)] + [
        distinct[-1] + 1e-6]
    best: tuple[float, ThresholdChoice] | None = None
    for t in candidates:
        refused_out = sum(s < t for s in out_scores) / len(out_scores)
        refused_in = sum(s < t for s in in_scores) / len(in_scores)
        balanced = (refused_out + (1 - refused_in)) / 2
        if best is None or balanced > best[0]:
            best = (balanced, ThresholdChoice(t, refused_out, refused_in))
    return best[1]


def margin_note(top: list[dict], threshold: float) -> str:
    """Margin between refused/non-refused scores, and the misclassified questions.

    Computed from `rerank_top`, not hardcoded, so it stays correct if the eval reruns.
    """
    in_domain = [(r["qid"], r["score"]) for r in top if r["in_domain"]]
    out_domain = [(r["qid"], r["score"]) for r in top if not r["in_domain"]]
    refused_out = [(q, s) for q, s in out_domain if s < threshold]
    non_refused_in = [(q, s) for q, s in in_domain if s >= threshold]
    wrongly_refused_in = [(q, s) for q, s in in_domain if s < threshold]
    not_refused_out = [(q, s) for q, s in out_domain if s >= threshold]
    highest_refused_out = max(refused_out, key=lambda qs: qs[1])
    lowest_non_refused_in = min(non_refused_in, key=lambda qs: qs[1])
    lines = [
        "## Margin",
        "",
        (f"- Highest refused out-of-domain score: {highest_refused_out[1]:.4f} "
         f"({highest_refused_out[0]})"),
        (f"- Lowest non-refused in-domain score: {lowest_non_refused_in[1]:.4f} "
         f"({lowest_non_refused_in[0]})"),
        "- Misclassified: " + "; ".join(
            [f"{q} not refused ({s:.4f})" for q, s in not_refused_out]
            + [f"{q} wrongly refused ({s:.4f})" for q, s in wrongly_refused_in]),
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    results = json.loads((REPO_ROOT / "eval" / "results" / "retrieval.json")
                         .read_text(encoding="utf-8"))
    top = results["rerank_top"]
    choice = choose_threshold([r["score"] for r in top if r["in_domain"]],
                              [r["score"] for r in top if not r["in_domain"]])
    out = REPO_ROOT / "eval" / "results"
    payload = {**asdict(choice), "threshold": round(choice.threshold, 4),
               "n_in_domain": sum(r["in_domain"] for r in top),
               "n_out_of_domain": sum(not r["in_domain"] for r in top)}
    (out / "refusal.json").write_text(json.dumps(payload, indent=1), encoding="utf-8")
    (out / "refusal.md").write_text(
        "# Refusal threshold\n\n"
        f"Refuse when the top reranker score is below **{payload['threshold']}**.\n\n"
        "| Metric | Value | Target (spec 8.2) |\n|---|---|---|\n"
        f"| Out-of-domain refused | {choice.refusal_accuracy:.1%} | ≥ 90% |\n"
        f"| In-domain wrongly refused | {choice.false_refusal_rate:.1%} | ≤ 10% |\n\n"
        "These figures are in-sample: the threshold was fitted on the same 80 in-domain + "
        "20 out-of-domain questions it is scored against, and 20 out-of-domain questions is "
        "a small sample, so treat the percentages as optimistic.\n\n"
        f"{margin_note(top, payload['threshold'])}",
        encoding="utf-8")
    print(json.dumps(payload))


if __name__ == "__main__":
    main()
