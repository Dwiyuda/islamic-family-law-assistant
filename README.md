# Islamic Family Law Assistant

A retrieval-augmented (RAG) assistant for **Indonesian Islamic family law** (for Muslims),
covering **divorce** and **inheritance**. It gives three grounded outputs — a case **Navigator**,
an **Inheritance Calculator** (*faraid*), and a cited **Q&A** — and it **refuses to answer when it
has no legal basis** in its sources. Every answer carries a disclaimer that it is not a substitute
for a lawyer.

> Built end-to-end as a portfolio project: corpus construction, hybrid retrieval with evaluation,
> grounded generation with refusal, a deterministic legal-arithmetic engine, and a containerised
> web app with CI.

## Highlights

| What | Result |
|---|---|
| Retrieval (hybrid + reranker, 80 in-domain questions) | **Recall@5 0.601**, MRR@10 0.702, nDCG@10 0.637 (vs. dense 0.575, BM25 0.223) |
| Out-of-domain refusal | **95.0%** refused · 1.2% in-domain wrongly refused *(in-sample)* |
| Grounded generation | **citation precision 1.000** across all groups · **100%** out-of-domain refused before answering |
| Answer quality (RAGAS, LLM-judged) | faithfulness **0.827**, answer relevancy 0.731 *(69 samples, partial)* |
| Inheritance engine | deterministic *faraid* over **KHI Book II (Art. 171–193)**, exact fractions, **104 textbook cases** |
| Corpus | **2,491 chunks** (regulations, Qur'an, hadith) with per-chunk provenance |
| Tests | **406 passing** |

Numbers come from `eval/results/` and are reported as-is; see [Evaluation](#evaluation) for the
honest caveats (in-sample thresholds, partial RAGAS run).

## How it works

```
                      ┌─────────── retrieval ───────────┐
question ──► BM25 + BGE-M3 (dense+sparse) ─► RRF (k=60) ─► bge-reranker-v2-m3 ─► top-k
                                                                   │
                        refusal gate (reranker score < threshold → refuse)
                                                                   │
            ┌──────────────────────────────────────────────────────┼─────────────────────────┐
            ▼                                                        ▼                         ▼
   Navigator (steps + articles)                       cited Q&A answer            Faraid calculator
   LLM drafts, validated to JSON,                      LLM, citations only         DETERMINISTIC engine
   citations from retrieved chunks                     from retrieved chunks       (fractions.Fraction);
                                                                                   LLM only explains,
                                                                                   never produces numbers
```

- **Sources of authority** (in order): regulations > Qur'an > sound/good hadith > books. Steps that
  rest only on weak (*dhaif*) hadith are dropped.
- **Numbers never come from the LLM.** Inheritance shares are computed by a rule engine from the
  *Kompilasi Hukum Islam* (KHI); the LLM only explains the legal basis. A guard in the service layer
  enforces this.
- **Refusal is first-class.** A reranker-score threshold rejects out-of-scope questions before the
  LLM is ever called, closing the leak of non-Muslim / out-of-domain queries.

## Features

| Route | Feature | Notes |
|------|--------|------|
| `/` | **Navigator** | Describe a situation → case type, competent court, documents, ordered steps, article citations (validated JSON). |
| `/waris` | **Inheritance Calculator** (*faraid*) | Enter the estate and heirs → each heir's share as an exact fraction + rupiah amount, with ʿawl/radd handling and an **"expert verification needed"** badge where the engine uses interpretation beyond the literal KHI text. |
| `/tanya` | **Q&A** | Cited answers over the corpus; refuses without a legal basis. |

## Tech stack

- **Retrieval:** Qdrant (embedded), BGE-M3 dense+sparse embeddings + BM25, reciprocal-rank fusion
  (k=60), `bge-reranker-v2-m3`. CPU-only.
- **Generation:** FastAPI service; LLM via an OpenAI-compatible client (Groq / Gemini), or `none`
  for retrieval-only. Responses are schema-validated with Pydantic.
- **Faraid engine:** pure-Python rule engine (`fractions.Fraction`) over KHI Book II.
- **Frontend:** Next.js (App Router, TypeScript, Tailwind CSS), 3 pages; browser calls the API
  directly via CORS.
- **Ops:** Docker Compose (2 services), GitHub Actions CI (pytest + Next.js build), RAGAS for
  evaluation, `pytest` (406 tests).

## Run it (Docker)

**Prerequisites**
- Corpus and index already built: `data/` and `data/qdrant`.
- BGE model cache present in `.cache/huggingface`.
- Docker Desktop installed and running.
- `.env` optional (LLM only — see below).

```bash
docker compose up --build
```

Then open `http://localhost:3000`. The API runs on `http://localhost:8000`
(`/health`, `/navigator`, `/ask`, `/faraid`).

**Notes**
- `api` startup takes ~1–2 min (models load on CPU); `web` waits for `api` to be healthy.
- `/ask` and `/navigator` take ~45 s per request on CPU (the reranker + LLM round-trip). `/faraid`
  is instant (deterministic).

**Optional LLM**
- No `.env` or `LLM_PROVIDER=none` → retrieval-only mode: shows the most relevant articles and
  evidence, without an LLM summary.
- `LLM_PROVIDER=groq` or `gemini` + an API key in `.env` → generated, cited answers.

## Evaluation

Methodology and full numbers live in `eval/results/` (`retrieval.md`, `refusal.md`, `generation.md`);
each file records its run configuration and the corpus hash it was measured on.

**Retrieval** — 80 in-domain gold questions:

| Method | Recall@5 | MRR@10 | nDCG@10 |
|---|---|---|---|
| BM25 | 0.223 | 0.305 | 0.257 |
| dense (BGE-M3) | 0.575 | 0.674 | 0.596 |
| hybrid | 0.428 | 0.549 | 0.474 |
| **hybrid + reranker** | **0.601** | **0.702** | **0.637** |

Reranking the fused candidates is the biggest single lever (Recall@5 0.428 → 0.601).

**Refusal** (threshold 0.0333): 95.0% of out-of-domain questions refused, 1.2% of in-domain
questions wrongly refused.

**Generation** (`gemini-flash-lite`): citation precision 1.000 in every group; 100% of out-of-domain
questions refused at the generation stage; Navigator kept 55/55 step citations; RAGAS faithfulness
0.827, answer relevancy 0.731.

**Honest caveats** (also noted in the result files):
- Refusal and in-sample generation thresholds were fitted on the same questions they are scored on,
  and the out-of-domain sample (20) is small — read those percentages as optimistic. A held-out set
  (`eval/heldout.jsonl`) is included for out-of-sample checks.
- The RAGAS run is **partial**: the free-tier LLM-judge quota ran out before the held-out split.
  Faithfulness (0.827) is just below the 0.85 target. RAGAS prompts are English while answers are
  Indonesian; treat small differences as noise.
- When the judge model equals the generator, it grades its own model family.

## Limitations

- **Faraid interpretation beyond the literal KHI.** Grandfather / grandmother and replacement heirs
  (*ahli waris pengganti*, Art. 185) are not fully specified by the KHI text; the engine applies an
  interpretation and flags those results with `perlu_verifikasi_ahli` ("needs expert verification").
  See [`docs/faraid-notes.md`](docs/faraid-notes.md) — **this requires review by a qualified
  Islamic-law / fiqh expert** and is not final.
- **Not legal advice.** General information only; consult a lawyer or the legal-aid desk (*Posbakum*)
  at a Religious Court (*Pengadilan Agama*).
- CPU-only; sized for a single-user local demo (one request at a time).
- Copyrighted *faraid* textbooks are kept in a private corpus and are never committed or shipped.

## Project layout

```
api/     FastAPI service: ingest, retrieval, generation, faraid engine, tests
web/     Next.js frontend (3 pages)
data/    corpus (chunks.jsonl) + Qdrant index   (large files git-ignored)
eval/    gold/held-out sets, evaluation scripts, result reports
docs/    design specs, source verification, faraid interpretation notes
```

---

*Built with Python 3.12, FastAPI, Next.js, and Qdrant.*
