"""Navigator and Q&A (spec 6): retrieve, ask the LLM for JSON, guard citations, or refuse."""

from __future__ import annotations

from collections.abc import Callable
import re
from dataclasses import dataclass

from pydantic import BaseModel

from app.config import REFUSAL_THRESHOLD, TOP_K
from app.faraid import FaraidResult
from app.ingest.models import Chunk
from app.retrieval.retriever import Hit

from .guard import GuardStats, guard_answer, guard_steps
from .prompts import context_block, messages
from .providers import LLMProvider, ProviderError, ProviderUnavailable
from .schemas import (
    OUT_OF_SCOPE_ADVICE,
    REFUSAL_ADVICE,
    RETRIEVAL_ONLY_NOTE,
    AskDraft,
    AskResponse,
    NavigatorDraft,
    NavigatorResponse,
    Sumber,
)
from .sources import notes_for, order_by_authority, to_sumber

NAVIGATOR_DOMAINS = {"perceraian", "peradilan", "prosedur"}  # spec 5: divorce navigator filter

Response = NavigatorResponse | AskResponse


class _PenjelasanDraft(BaseModel):
    penjelasan: str


_FARAID_SYSTEM = (
    "Kamu menarasikan hasil hitung waris (faraid) dalam bahasa Indonesia yang ringkas. "
    "Semua angka sudah dihitung mesin; tulis ulang apa adanya, JANGAN menghitung, "
    "mengubah, atau menambah angka/pecahan/dalil baru. Jangan memberi fatwa. "
    'Balas JSON: {"penjelasan": "<2-5 kalimat>"}.')


def _angka(teks: str) -> set[str]:
    return set(re.findall(r"\d+", re.sub(r"(?<=\d)[.,](?=\d)", "", teks)))


@dataclass(frozen=True)
class Outcome:
    response: Response
    retrieved: list[str]  # chunk ids given to the LLM, in authority order
    top_score: float
    draft: dict | None = None  # validated LLM output before the guard (for evaluation)
    stats: GuardStats | None = None
    provider_failed: bool = False


def _reply(kind: str, status: str, text: str, mode: str, **fields) -> Response:
    if kind == "navigator":
        return NavigatorResponse(status=status, ringkasan=text, mode=mode, **fields)
    return AskResponse(status=status, jawaban=text, mode=mode, **fields)


class Assistant:
    def __init__(self, chunks: dict[str, Chunk], provider: LLMProvider | None,
                 search: Callable[..., list[Hit]] | None = None,
                 threshold: float = REFUSAL_THRESHOLD, top_k: int = TOP_K):
        self.chunks, self.provider, self.search = chunks, provider, search
        self.threshold, self.top_k = threshold, top_k

    def navigator(self, question: str) -> Outcome:
        hits = self.search(question, top_k=self.top_k, method="hybrid_rerank",
                           domains=NAVIGATOR_DOMAINS)
        return self.answer_from_hits("navigator", question, hits)

    def ask(self, question: str) -> Outcome:
        hits = self.search(question, top_k=self.top_k, method="hybrid_rerank")
        return self.answer_from_hits("ask", question, hits)

    def answer_from_hits(self, kind: str, question: str, hits: list[Hit]) -> Outcome:
        """Everything after retrieval; evaluation replays cached hits through this."""
        mode = "llm" if self.provider else "retrieval_only"
        top = (hits[0].rerank_score or 0.0) if hits else 0.0
        if top < self.threshold:  # also covers "nothing retrieved"
            return Outcome(_reply(kind, "ditolak", REFUSAL_ADVICE, mode), [], top)
        ids = order_by_authority([h.chunk_id for h in hits], self.chunks)
        sumber = [to_sumber(self.chunks[cid]) for cid in ids]
        if self.provider is None:
            return Outcome(self._retrieval_only(kind, ids, sumber), ids, top)
        schema = NavigatorDraft if kind == "navigator" else AskDraft
        try:
            draft = self.provider.complete(messages(kind, question,
                                                    context_block(ids, self.chunks)), schema)
        except ProviderError as exc:
            return Outcome(self._retrieval_only(kind, ids, sumber), ids, top,
                           provider_failed=isinstance(exc, ProviderUnavailable))
        if draft["status"] == "di_luar_cakupan":
            return Outcome(_reply(kind, "di_luar_cakupan", OUT_OF_SCOPE_ADVICE, "llm"),
                           ids, top, draft)
        if kind == "navigator":
            nav = NavigatorDraft.model_validate(draft)
            steps, stats = guard_steps(nav.langkah, ids, self.chunks)
            if not steps:
                return Outcome(_reply(kind, "ditolak", REFUSAL_ADVICE, "llm"), ids, top,
                               draft, stats)
            cited = list(dict.fromkeys(c for step in steps for c in step.sitasi))
            response = NavigatorResponse(
                status="ok", jenis_perkara=nav.jenis_perkara, pengadilan=nav.pengadilan,
                ringkasan=nav.ringkasan, langkah=steps,
                peringatan=nav.peringatan + notes_for(cited, self.chunks), sumber=sumber,
                mode="llm")
            return Outcome(response, ids, top, draft, stats)
        ask = AskDraft.model_validate(draft)
        cited, stats = guard_answer(ask.sitasi, ids, self.chunks)
        if not cited or not ask.jawaban.strip():  # an empty answer is unusable, not an answer
            return Outcome(_reply(kind, "ditolak", REFUSAL_ADVICE, "llm"), ids, top, draft,
                           stats)
        response = AskResponse(status="ok", jawaban=ask.jawaban, sitasi=cited,
                               peringatan=notes_for(cited, self.chunks), sumber=sumber,
                               mode="llm")
        return Outcome(response, ids, top, draft, stats)

    def _retrieval_only(self, kind: str, ids: list[str], sumber: list[Sumber]) -> Response:
        fields = {"peringatan": notes_for(ids, self.chunks), "sumber": sumber}
        if kind == "ask":
            fields["sitasi"] = ids
        return _reply(kind, "ok", RETRIEVAL_ONLY_NOTE, "retrieval_only", **fields)

    def jelaskan_faraid(self, result: FaraidResult) -> str | None:
        """Narrate an engine result. Numbers come only from `result`; a narration that
        contains any number not in the facts is discarded (-> None)."""
        if self.provider is None or result.status != "ok":
            return None
        fakta = "\n".join(
            f"- {b.ahli_waris} (x{b.jumlah}): {b.bagian_pembilang}/{b.bagian_penyebut}, "
            f"Rp {b.nominal}, dasar: {'; '.join(b.dasar)}" for b in result.bagian)
        fakta += f"\naul: {result.aul_terjadi}; radd: {result.radd_terjadi}"
        fakta += "\n" + result.disclaimer
        try:
            teks = self.provider.complete(
                [{"role": "system", "content": _FARAID_SYSTEM},
                 {"role": "user", "content": fakta}], _PenjelasanDraft)["penjelasan"].strip()
        except ProviderError:
            return None
        return teks if teks and _angka(teks) <= _angka(fakta) else None
