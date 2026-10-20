from __future__ import annotations

import argparse
import json
import time
from collections.abc import Callable
from pathlib import Path

from app.config import DEFAULT_DEVICE
from app.ingest.models import Chunk

from .bm25 import BM25Index
from .corpus import index_text, load_corpus
from .index_manifest import (
    MANIFEST_NAME,
    MODEL_NAME,
    corpus_hashes,
    diff,
    read_manifest,
    write_manifest,
)
from .models import Embedder, Reranker
from .qdrant_store import QdrantStore
from .retriever import Retriever
from .thermal import wait_until_cool


def build_index(chunks: list[Chunk], embedder: Embedder, store: QdrantStore,
                batch_size: int = 32, pause: float = 0.0,
                cool: Callable[[], None] | None = None) -> int:
    store.recreate(embedder.dim)
    for start in range(0, len(chunks), batch_size):
        if cool is not None:
            cool()
        batch = chunks[start:start + batch_size]
        store.upsert(batch, embedder.encode([index_text(c) for c in batch]))
        if pause > 0:
            time.sleep(pause)  # ponytail: lets a watched GPU cool between batches
    return store.count()


def update_index(chunks: list[Chunk], embedder: Embedder, store: QdrantStore,
                 changed: list[str], removed: list[str], batch_size: int = 32,
                 cool: Callable[[], None] | None = None) -> int:
    """Re-embed only `changed` chunks and delete `removed` ones; returns chunks embedded."""
    wanted = set(changed)
    subset = [c for c in chunks if c.chunk_id in wanted]
    store.delete(removed)
    for start in range(0, len(subset), batch_size):
        if cool is not None:
            cool()
        batch = subset[start:start + batch_size]
        store.upsert(batch, embedder.encode([index_text(c) for c in batch]))
    return len(subset)


def rebuild(chunks: list[Chunk], embedder: Embedder, store: QdrantStore, qdrant_path: Path,
            max_length: int, **build_kwargs) -> int:
    """Full build; the manifest is removed first and written last, so an aborted build
    leaves no manifest and the partial index is rejected."""
    (qdrant_path / MANIFEST_NAME).unlink(missing_ok=True)
    indexed = build_index(chunks, embedder, store, **build_kwargs)
    write_manifest(qdrant_path, corpus_hashes(chunks), max_length)
    return indexed


def open_retriever(data_dir: Path, qdrant_path: Path, embedder: Embedder,
                   reranker: Reranker | None = None) -> Retriever:
    chunks = load_corpus(data_dir)
    manifest = read_manifest(qdrant_path)
    if manifest is None:
        raise RuntimeError("Qdrant index has no manifest: rebuild it with a full"
                           " `python -m app.retrieval.indexer` (`--incremental` only works"
                           " on an index that already has a manifest)")
    changed, removed = diff(manifest, corpus_hashes(chunks))
    if changed or removed:
        raise RuntimeError(f"Qdrant index is out of date: {len(changed)} changed, "
                           f"{len(removed)} removed; run `python -m app.retrieval.indexer"
                           " --incremental`")
    store = QdrantStore.local(qdrant_path)
    try:
        held = store.count()
        if held != len(manifest["chunks"]):
            raise RuntimeError(f"Qdrant index is incomplete: holds {held} points, manifest "
                               f"lists {len(manifest['chunks'])}; run a full index")
    except BaseException:
        store.close()
        raise
    return Retriever(chunks, BM25Index(chunks), store, embedder, reranker)


def main() -> None:
    from .models import BGEM3Embedder

    parser = argparse.ArgumentParser(description="Embed the corpus into Qdrant (local mode)")
    parser.add_argument("--data-dir", type=Path, default=Path("../data"))
    parser.add_argument("--qdrant-path", type=Path, default=Path("../data/qdrant"))
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--pause", type=float, default=0.0)
    parser.add_argument("--max-length", type=int, default=1024)
    parser.add_argument("--max-gpu-temp", type=int, default=0,
                        help="pause batches until the GPU cools below --resume-gpu-temp"
                             " (0 = off)")
    parser.add_argument("--resume-gpu-temp", type=int, default=68)
    parser.add_argument("--device", default=DEFAULT_DEVICE,
                        help="e.g. 'cpu' or 'cuda:0'; defaults to IFLA_DEVICE env var or 'cpu'")
    parser.add_argument("--threads", type=int, default=0,
                        help="torch.set_num_threads; 0 = leave torch's default")
    parser.add_argument("--incremental", action="store_true",
                        help="re-embed only chunks whose text changed since the manifest")
    args = parser.parse_args()
    if args.threads > 0:
        import torch

        torch.set_num_threads(args.threads)
    chunks = load_corpus(args.data_dir)
    started = time.perf_counter()
    store = QdrantStore.local(args.qdrant_path)
    cooldown_total = 0.0

    def cool() -> None:
        nonlocal cooldown_total
        cooldown_total += wait_until_cool(args.max_gpu_temp, args.resume_gpu_temp)

    hashes = corpus_hashes(chunks)
    try:
        if args.incremental:
            manifest = read_manifest(args.qdrant_path)
            if (manifest is None or manifest["model"] != MODEL_NAME
                    or manifest["max_length"] != args.max_length):
                raise SystemExit("cannot run --incremental: manifest is missing or was built "
                                 "with a different model/max_length; run a full index")
            changed, removed = diff(manifest, hashes)
            embedded = 0
            if changed or removed:
                embedder = (BGEM3Embedder(max_length=args.max_length, device=args.device)
                            if changed else None)
                embedded = update_index(chunks, embedder, store, changed, removed,
                                        args.batch_size, cool)
            write_manifest(args.qdrant_path, hashes, args.max_length)
            print(json.dumps({"changed": len(changed), "removed": len(removed),
                              "embedded": embedded,
                              "seconds": round(time.perf_counter() - started, 1)}))
            return
        embedder = BGEM3Embedder(max_length=args.max_length, device=args.device)
        indexed = rebuild(chunks, embedder, store, args.qdrant_path, args.max_length,
                          batch_size=args.batch_size, pause=args.pause, cool=cool)
    finally:
        store.close()
    print(json.dumps({"chunks": len(chunks), "indexed": indexed,
                      "seconds": round(time.perf_counter() - started, 1),
                      "cooldown_seconds": round(cooldown_total, 1)}))

if __name__ == "__main__":
    main()
