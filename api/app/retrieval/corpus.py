from __future__ import annotations

from pathlib import Path

from app.ingest.jsonl import read_chunks
from app.ingest.models import Chunk

REPO_ROOT = Path(__file__).resolve().parents[3]


def load_corpus(data_dir: Path) -> list[Chunk]:
    return read_chunks(data_dir / "processed" / "chunks.jsonl")


def index_text(chunk: Chunk) -> str:
    """What every retriever sees: the citation (so "Pasal 116" matches) plus the text."""
    return f"{chunk.citation}\n{chunk.text}"
