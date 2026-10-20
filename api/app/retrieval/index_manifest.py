"""Content hashes of the indexed chunks, stored next to the Qdrant folder, so a corpus fix
that changes text without changing the chunk count is detected, and only changed chunks
are re-embedded."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.ingest.models import Chunk

from .corpus import index_text

MANIFEST_NAME = "index_manifest.json"
MODEL_NAME = "BAAI/bge-m3"


def text_hash(chunk: Chunk) -> str:
    return hashlib.sha256(index_text(chunk).encode("utf-8")).hexdigest()


def corpus_hashes(chunks: list[Chunk]) -> dict[str, str]:
    return {c.chunk_id: text_hash(c) for c in chunks}


def read_manifest(qdrant_path: Path) -> dict | None:
    path = qdrant_path / MANIFEST_NAME
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def write_manifest(qdrant_path: Path, hashes: dict[str, str], max_length: int,
                   model: str = MODEL_NAME) -> None:
    qdrant_path.mkdir(parents=True, exist_ok=True)
    payload = {"model": model, "max_length": max_length, "chunks": dict(sorted(hashes.items()))}
    (qdrant_path / MANIFEST_NAME).write_text(json.dumps(payload, indent=0), encoding="utf-8")


def diff(manifest: dict, hashes: dict[str, str]) -> tuple[list[str], list[str]]:
    """(chunk ids to (re-)embed, chunk ids to delete) to bring the index up to `hashes`."""
    old = manifest["chunks"]
    changed = sorted(cid for cid, h in hashes.items() if old.get(cid) != h)
    removed = sorted(set(old) - set(hashes))
    return changed, removed
