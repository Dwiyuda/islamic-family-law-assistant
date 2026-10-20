import os
from collections.abc import Iterable
from pathlib import Path

from .models import Chunk


def write_chunks(path: Path, chunks: Iterable[Chunk]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    # Materialize and validate all chunks before writing
    chunks_list = list(chunks)
    seen: set[str] = set()
    for chunk in chunks_list:
        if chunk.chunk_id in seen:
            raise ValueError(f"duplicate chunk_id: {chunk.chunk_id}")
        seen.add(chunk.chunk_id)
    # Write to temporary file, then atomically replace
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8", newline="\n") as f:
        for chunk in chunks_list:
            f.write(chunk.model_dump_json() + "\n")
    os.replace(str(tmp_path), str(path))
    return len(chunks_list)


def read_chunks(path: Path) -> list[Chunk]:
    with path.open(encoding="utf-8") as f:
        return [Chunk.model_validate_json(line) for line in f if line.strip()]
