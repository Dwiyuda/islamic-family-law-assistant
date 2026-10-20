from __future__ import annotations

import re
import unicodedata

from rank_bm25 import BM25Okapi

from app.ingest.models import Chunk

from .corpus import index_text

_WORD = re.compile(r"\w+")


def tokenize(text: str) -> list[str]:
    """Spec 5: lowercase, drop punctuation. Combining marks (harakat, Latin accents) are
    removed first so voweled Arabic stays one token per word."""
    bare = "".join(ch for ch in unicodedata.normalize("NFKD", text)
                   if not unicodedata.combining(ch))
    return _WORD.findall(bare.lower())


class BM25Index:
    def __init__(self, chunks: list[Chunk]):
        self._ids = [c.chunk_id for c in chunks]
        self._bm25 = BM25Okapi([tokenize(index_text(c)) for c in chunks])

    def search(
        self, query: str, top_k: int, allowed: set[str] | None = None
    ) -> list[tuple[str, float]]:
        scores = self._bm25.get_scores(tokenize(query))
        hits: list[tuple[str, float]] = []
        for i in sorted(range(len(scores)), key=lambda i: -scores[i]):
            if scores[i] <= 0 or len(hits) == top_k:
                break
            if allowed is None or self._ids[i] in allowed:
                hits.append((self._ids[i], float(scores[i])))
        return hits
