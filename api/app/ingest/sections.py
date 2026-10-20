from __future__ import annotations

import re
from typing import Literal

from bs4 import BeautifulSoup

from .models import MAX_TOKENS, Chunk, approx_tokens
from .sources import Source


def _split_oversized(paragraph: str) -> list[str]:
    sentences = re.split(r"(?<=\.)\s+", paragraph)
    pieces: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = f"{current} {sentence}".strip()
        if current and approx_tokens(candidate) > MAX_TOKENS:
            pieces.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        pieces.append(current)
    return pieces


def chunk_sections(
    text: str, source: Source, source_type: Literal["procedure", "kitab", "book"]
) -> list[Chunk]:
    paragraphs: list[str] = []
    for para in re.split(r"\n\s*\n", text):
        para = para.strip()
        if not para:
            continue
        paragraphs.extend(_split_oversized(para) if approx_tokens(para) > MAX_TOKENS else [para])

    packed: list[str] = []
    for para in paragraphs:
        if packed and approx_tokens(packed[-1] + "\n\n" + para) <= MAX_TOKENS:
            packed[-1] = packed[-1] + "\n\n" + para
        else:
            packed.append(para)

    return [
        Chunk(
            chunk_id=f"{source.doc_id}:bagian-{i}", doc_id=source.doc_id, doc_title=source.judul,
            source_type=source_type, domain=source.domain, hierarchy={"bagian": str(i)},
            citation=f"{source.singkatan}, bagian {i}", text=body,
            source_url=source.url_sumber, status=source.status, license=source.lisensi,
            visibility=source.visibility,
        )
        for i, body in enumerate(packed, start=1)
    ]


def _list_text(text: str) -> str:
    lines = (line.strip() for line in text.splitlines())
    return "\n".join(line for line in lines if line and line != "-")


def chunk_procedure_html(html: str, source: Source) -> list[Chunk]:
    soup = BeautifulSoup(html, "html.parser")
    root = soup.select_one(source.html_selector) if source.html_selector else soup.body
    if root is None:
        raise ValueError(f"{source.doc_id}: selector {source.html_selector!r} matched nothing")
    lists = [lst for lst in root.find_all(["ol", "ul"]) if lst.find_parent(["ol", "ul"]) is None]
    if source.procedure_unit == "step":
        label = "langkah"
        units = [_list_text(li.get_text("\n", strip=True))
                 for lst in lists for li in lst.find_all("li", recursive=False)]
    else:
        label = "bagian"
        units = []
        for lst in lists:
            heading = lst.find_previous_sibling()
            prefix = heading.get_text(" ", strip=True) if heading is not None else ""
            body = _list_text(lst.get_text("\n", strip=True))
            units.append(f"{prefix}\n{body}" if 0 < len(prefix) <= 120 else body)
    return [
        Chunk(
            chunk_id=f"{source.doc_id}:{label}-{i}", doc_id=source.doc_id,
            doc_title=source.judul, source_type="procedure", domain=source.domain,
            hierarchy={label: str(i)}, citation=f"{source.singkatan} {label} {i}", text=text,
            source_url=source.url_sumber, status=source.status, license=source.lisensi,
            visibility=source.visibility,
        )
        for i, text in enumerate((u for u in units if u), start=1)
    ]
