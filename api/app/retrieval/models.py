from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Protocol

from app.config import DEFAULT_DEVICE

from .corpus import REPO_ROOT


@dataclass(frozen=True)
class Encoded:
    dense: list[float]
    sparse: dict[int, float]


class Embedder(Protocol):
    dim: int

    def encode(self, texts: list[str]) -> list[Encoded]: ...


class Reranker(Protocol):
    def score(self, query: str, texts: list[str]) -> list[float]: ...


def _use_repo_hf_cache() -> None:
    # Drive C is nearly full: keep Hugging Face downloads in the repo on D (git-ignored).
    os.environ.setdefault("HF_HOME", str(REPO_ROOT / ".cache" / "huggingface"))
    # After the one-time download, set HF_HUB_OFFLINE=1: FlagEmbedding's snapshot_download
    # otherwise re-checks the repo and, if the unused onnx/ shard is absent or incomplete,
    # tries to fetch it over the network (confirmed: it raised IncompleteSnapshotError and
    # attempted an online fetch here even though the pytorch weights were already complete).


class BGEM3Embedder:
    """BGE-M3 dense (1024-d) + sparse lexical weights in one pass."""

    dim = 1024

    def __init__(self, model_name: str = "BAAI/bge-m3", use_fp16: bool = True,
                 batch_size: int = 8, max_length: int = 2048, device: str | None = DEFAULT_DEVICE):
        _use_repo_hf_cache()
        from FlagEmbedding import BGEM3FlagModel

        if device == "cpu":
            use_fp16 = False  # fp16 matmul isn't supported on CPU
        self._model = BGEM3FlagModel(model_name, use_fp16=use_fp16, devices=device)
        # ponytail: 2048-token cap truncates the longest merged Muslim hadith (~4k tokens);
        # raise it if those chunks show up as misses in the eval.
        self._batch_size, self._max_length = batch_size, max_length

    def encode(self, texts: list[str]) -> list[Encoded]:
        out = self._model.encode(texts, batch_size=self._batch_size, max_length=self._max_length,
                                 return_dense=True, return_sparse=True,
                                 return_colbert_vecs=False)
        return [
            Encoded(dense=[float(x) for x in dense],
                    sparse={int(k): float(v) for k, v in weights.items()} or {0: 0.0})
            for dense, weights in zip(out["dense_vecs"], out["lexical_weights"], strict=True)
        ]


class BGEReranker:
    """Cross-encoder; scores normalized to 0..1 so a refusal threshold is meaningful."""

    def __init__(self, model_name: str = "BAAI/bge-reranker-v2-m3", use_fp16: bool = True,
                 batch_size: int = 16, max_length: int = 512,
                 device: str | None = DEFAULT_DEVICE):
        _use_repo_hf_cache()
        from FlagEmbedding import FlagReranker

        if device == "cpu":
            use_fp16 = False  # fp16 matmul isn't supported on CPU
        self._model = FlagReranker(model_name, use_fp16=use_fp16, devices=device)
        # Fase 1 ruling: long hadith stay whole in storage and are truncated only here.
        # CPU latency (~45s/query at 512 with 8 threads vs ~90-110s at 1024).
        self._batch_size, self._max_length = batch_size, max_length

    def score(self, query: str, texts: list[str]) -> list[float]:
        if not texts:
            return []
        scores = self._model.compute_score([[query, t] for t in texts],
                                           batch_size=self._batch_size,
                                           max_length=self._max_length, normalize=True)
        return [float(s) for s in (scores if isinstance(scores, list) else [scores])]
