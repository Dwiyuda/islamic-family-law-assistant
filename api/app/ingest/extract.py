from __future__ import annotations

import re
from pathlib import Path

from bs4 import BeautifulSoup
from pypdf import PdfReader

_PAGE_NUMBER = re.compile(r"^(\d{1,4}|-\s?\d{1,4}\s?-)$")
_SPACES = re.compile(r"[ \t ]+")


def normalize(text: str) -> str:
    """Unify newlines/spaces, drop bare page numbers, collapse 3+ blank lines to one blank
    line. Also join a soft hyphen (U+00AD) immediately followed by a line break — the word
    continues on the next line, e.g. "perka­\nwinan" -> "perkawinan" — and drop any
    other soft hyphen outright (it splits words for BM25 without adding meaning)."""
    lines = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = _SPACES.sub(" ", raw).strip()
        if _PAGE_NUMBER.match(line):
            continue
        lines.append(line)
    joined = "\n".join(lines)
    joined = joined.replace("­\n", "").replace("­", "")
    joined = re.sub(r"\n{3,}", "\n\n", joined)
    return joined.strip()


def _html_text(path: Path) -> str:
    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="ignore"), "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript"]):
        tag.decompose()
    return soup.get_text("\n")


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        raw = "\n".join((page.extract_text() or "") for page in PdfReader(path).pages)
    elif suffix == ".html":
        raw = _html_text(path)
    elif suffix == ".txt":
        raw = path.read_text(encoding="utf-8", errors="ignore")
    else:
        raise ValueError(f"unsupported format: {path.suffix}")
    return normalize(raw)
