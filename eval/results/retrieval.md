# Retrieval evaluation

80 in-domain questions from `eval/gold.jsonl`.

| Method | Recall@5 | MRR@10 | nDCG@10 |
|---|---|---|---|
| bm25 | 0.223 | 0.305 | 0.257 |
| dense | 0.575 | 0.674 | 0.596 |
| hybrid | 0.428 | 0.549 | 0.474 |
| hybrid_rerank | 0.601 | 0.702 | 0.637 |

## Run configuration

- device: `cpu`, threads: 8
- reranker max_length: 512
- RERANK_CANDIDATES: 30, TOP_K: 8
- library versions: FlagEmbedding 1.4.2, torch 2.6.0+cpu, qdrant-client 1.19.1, rank-bm25 0.2.2
- chunks.jsonl sha256: `de2c56ea7becafb984dbda7538f0f4143b721cb8042f5cbfe49e43812c865666`
- date: 2026-10-06
