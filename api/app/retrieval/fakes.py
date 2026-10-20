"""Deterministic stand-ins for the models: unit tests and CI never download weights."""

from __future__ import annotations

import math
import re
import zlib

from .models import Encoded

_WORD = re.compile(r"\w+")


def _tokens(text: str) -> list[str]:
    return _WORD.findall(text.lower())


class HashEmbedder:
    def __init__(self, dim: int = 256):
        self.dim = dim

    def encode(self, texts: list[str]) -> list[Encoded]:
        out: list[Encoded] = []
        for text in texts:
            sparse: dict[int, float] = {}
            for token in _tokens(text):
                key = zlib.crc32(token.encode()) % 100_003
                sparse[key] = sparse.get(key, 0.0) + 1.0
            dense = [0.0] * self.dim
            for key, weight in sparse.items():
                dense[key % self.dim] += weight
            norm = math.sqrt(sum(x * x for x in dense)) or 1.0
            out.append(Encoded(dense=[x / norm for x in dense], sparse=sparse or {0: 0.0}))
        return out


class OverlapReranker:
    """Share of query words present in the text (0..1)."""

    def score(self, query: str, texts: list[str]) -> list[float]:
        words = set(_tokens(query))
        return [len(words & set(_tokens(t))) / len(words) if words else 0.0 for t in texts]
