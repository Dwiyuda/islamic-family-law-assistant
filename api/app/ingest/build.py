from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from .extract import extract_text
from .hadeethenc import parse_hadeethenc
from .hadith import COLLECTIONS, parse_hadith
from .jsonl import write_chunks
from .models import Chunk
from .quran import parse_quran
from .regulation import deleted_pasal, mark_amendments, parse_regulation
from .sections import chunk_procedure_html, chunk_sections
from .sources import load_sources, raw_path

REGULATION_TYPES = {"uu", "pp", "inpres", "perma"}


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_public(data_dir: Path) -> list[Chunk]:
    raw_dir = data_dir / "raw"
    sources = {s.doc_id: s for s in load_sources(data_dir / "sources.yaml")}
    chunks: list[Chunk] = []
    deletions: dict[str, set[str]] = {}
    for source in sources.values():
        if source.role == "reference":
            continue
        if source.jenis in REGULATION_TYPES:
            text = extract_text(raw_path(source, raw_dir))
            chunks += parse_regulation(text, source)
            if source.amends:
                deletions[source.doc_id] = deleted_pasal(text)
        elif source.jenis == "prosedur" and source.html_selector:
            html = raw_path(source, raw_dir).read_bytes().decode("utf-8", errors="replace")
            chunks += chunk_procedure_html(html, source)
        elif source.jenis == "prosedur":
            chunks += chunk_sections(extract_text(raw_path(source, raw_dir)), source, "procedure")
        elif source.jenis == "kitab":
            chunks += chunk_sections(extract_text(raw_path(source, raw_dir)), source, "kitab")
        elif source.fetcher == "hadeethenc":
            chunks += parse_hadeethenc(_load_json(raw_path(source, raw_dir)), source)

    if {"quran-ara", "quran-ind"} <= sources.keys():
        ara, ind = sources["quran-ara"], sources["quran-ind"]
        chunks += parse_quran(_load_json(raw_path(ara, raw_dir)),
                              _load_json(raw_path(ind, raw_dir)), ara, ind)

    if "hadis-info" in sources:
        info = _load_json(raw_path(sources["hadis-info"], raw_dir))
        for collection in COLLECTIONS:
            ara = sources.get(f"hadis-{collection}-ara")
            if ara and collection in info:
                chunks += parse_hadith(collection, _load_json(raw_path(ara, raw_dir)), info, ara)

    chunks = mark_amendments(chunks, sources, deletions)
    leaked = [c.chunk_id for c in chunks if c.visibility != "public"]
    if leaked:
        raise ValueError(f"non-public chunks in public build: {leaked[:5]}")
    return chunks


def build_private(data_dir: Path) -> list[Chunk]:
    manifest = data_dir / "private" / "sources_private.yaml"
    if not manifest.exists():
        return []
    raw_dir = data_dir / "private" / "raw"
    chunks: list[Chunk] = []
    for source in load_sources(manifest, expect_visibility="private"):
        if source.jenis == "buku":
            chunks += chunk_sections(extract_text(raw_path(source, raw_dir)), source, "book")
    return chunks


def stats(chunks: list[Chunk]) -> dict:
    return {
        "total": len(chunks),
        "by_source_type": dict(Counter(c.source_type for c in chunks)),
        "by_domain": dict(Counter(c.domain for c in chunks)),
        "by_doc": dict(Counter(c.doc_id for c in chunks)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build chunk files from the manifest")
    parser.add_argument("--data-dir", type=Path, default=Path("../data"))
    args = parser.parse_args()
    public = build_public(args.data_dir)
    write_chunks(args.data_dir / "processed" / "chunks.jsonl", public)
    summary = stats(public)
    (args.data_dir / "processed" / "stats.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    private = build_private(args.data_dir)
    if private:
        write_chunks(args.data_dir / "private" / "chunks_private.jsonl", private)
    print(json.dumps({"public": summary["total"], "private": len(private),
                      "by_source_type": summary["by_source_type"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
