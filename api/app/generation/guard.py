"""Citation guard (spec 6.3): keep only retrieved, non-weak-only citations."""

from __future__ import annotations

from dataclasses import dataclass

from app.ingest.models import Chunk

from .schemas import Langkah
from .sources import is_weak


@dataclass(frozen=True)
class GuardStats:
    citations_total: int  # as the LLM wrote them (spec 8.2 citation precision denominator)
    citations_valid: int  # of those, ids that were actually retrieved
    steps_total: int
    steps_kept: int


def _valid(sitasi: list[str], allowed: set[str]) -> list[str]:
    return list(dict.fromkeys(s for s in sitasi if s in allowed))


def _supported(cited: list[str], chunks: dict[str, Chunk]) -> bool:
    return bool(cited) and not all(is_weak(chunks[c]) for c in cited)


def guard_steps(langkah: list[Langkah], retrieved: list[str],
                chunks: dict[str, Chunk]) -> tuple[list[Langkah], GuardStats]:
    allowed = set(retrieved)
    kept: list[Langkah] = []
    total = valid = 0
    for step in langkah:
        total += len(step.sitasi)
        valid += sum(s in allowed for s in step.sitasi)
        cited = _valid(step.sitasi, allowed)
        if _supported(cited, chunks):
            kept.append(step.model_copy(update={"sitasi": cited}))
    kept = [s.model_copy(update={"urutan": i}) for i, s in enumerate(kept, start=1)]
    return kept, GuardStats(total, valid, len(langkah), len(kept))


def guard_answer(sitasi: list[str], retrieved: list[str],
                 chunks: dict[str, Chunk]) -> tuple[list[str], GuardStats]:
    allowed = set(retrieved)
    cited = _valid(sitasi, allowed)
    if not _supported(cited, chunks):
        cited = []
    return cited, GuardStats(len(sitasi), sum(s in allowed for s in sitasi), 1, int(bool(cited)))
