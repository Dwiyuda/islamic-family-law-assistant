from __future__ import annotations

from dataclasses import dataclass

from app.config import RERANK_CANDIDATES, TOP_K
from app.ingest.models import Chunk

from .bm25 import BM25Index
from .corpus import index_text
from .fusion import rrf
from .models import Embedder, Reranker
from .qdrant_store import QdrantStore

METHODS = ("bm25", "dense", "hybrid", "hybrid_rerank")


@dataclass(frozen=True)
class Hit:
    """`score` is method-specific and not comparable across methods (BM25 score, cosine
    similarity, or RRF sum); refusal decisions use `rerank_score` (0-1, only for
    `hybrid_rerank`)."""

    chunk_id: str
    score: float
    rerank_score: float | None = None


class Retriever:
    def __init__(self, chunks: list[Chunk], bm25: BM25Index, store: QdrantStore,
                 embedder: Embedder, reranker: Reranker | None = None):
        self.chunks = {c.chunk_id: c for c in chunks}
        self.bm25, self.store, self.embedder, self.reranker = bm25, store, embedder, reranker

    def search(self, query: str, top_k: int = TOP_K, method: str = "hybrid_rerank",
               domains: set[str] | None = None) -> list[Hit]:
        if method not in METHODS:
            raise ValueError(f"unknown method {method!r}; expected one of {METHODS}")
        if method == "hybrid_rerank" and self.reranker is None:
            raise ValueError("hybrid_rerank needs a reranker")
        allowed = ({cid for cid, c in self.chunks.items() if c.domain in domains}
                   if domains else None)
        if method == "bm25":
            return [Hit(cid, s) for cid, s in self.bm25.search(query, top_k, allowed)]

        [encoded] = self.embedder.encode([query])
        pool = top_k if method == "dense" else max(top_k, RERANK_CANDIDATES)
        dense = self.store.search("dense", encoded, pool, domains)
        if method == "dense":
            return [Hit(cid, s) for cid, s in dense]

        sparse = self.store.search("sparse", encoded, pool, domains)
        lexical = self.bm25.search(query, pool, allowed)
        fused = rrf([[cid for cid, _ in ranking] for ranking in (lexical, dense, sparse)])
        if method == "hybrid":
            return [Hit(cid, s) for cid, s in fused[:top_k]]

        candidates = fused[:RERANK_CANDIDATES]
        scores = self.reranker.score(query, [index_text(self.chunks[cid])
                                             for cid, _ in candidates])
        ranked = sorted(zip(candidates, scores, strict=True), key=lambda item: -item[1])
        return [Hit(cid, fused_score, rerank) for (cid, fused_score), rerank in ranked[:top_k]]
