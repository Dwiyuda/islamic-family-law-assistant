"""Crash-safe JSONL reading shared by the generation evaluation and its report."""

from __future__ import annotations

import json
import os
from pathlib import Path


def read_jsonl_rows(path: Path) -> list[dict]:
    """Rows of a JSONL file. Splits on "\n" only: U+2028/U+0085 can occur inside LLM text and
    str.splitlines() would cut there. A torn LAST line (crash mid-append) is dropped and the
    file rewritten atomically; an unparseable earlier line is real corruption and exits."""
    if not path.exists():
        return []
    lines = [(n, line) for n, line in
             enumerate(path.read_text(encoding="utf-8").split("\n"), start=1) if line.strip()]
    rows = []
    for i, (n, line) in enumerate(lines):
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            if i < len(lines) - 1:
                raise SystemExit(f"Corrupted JSONL line in {path} at line {n}") from None
            tmp = path.with_name(path.name + ".tmp")
            with tmp.open("w", encoding="utf-8", newline="\n") as fh:
                fh.writelines(good.rstrip("\r") + "\n" for _, good in lines[:-1])
            os.replace(str(tmp), str(path))
    return rows
