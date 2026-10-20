from __future__ import annotations

import re

from .models import MAX_TOKENS, Chunk, approx_tokens
from .sources import Source

# Ruling A: tolerant whitespace + lowercase-l-as-I OCR noise in the numeral.
RE_BUKU = re.compile(r"^BUKU\s*([IVXLCl]+)\b")
RE_BAB = re.compile(r"^BA[BHD]\s*([IVXLCl]+)\b")
RE_BAGIAN = re.compile(r"^Bagian\s+(Ke[a-z]+)\b", re.IGNORECASE)
# Ruling C: OCR drops the space before the numeral, sometimes even misreads the
# final "l" of the word "Pasal" itself as digit "1" (e.g. "Pasa124" = Pasal 24),
# and misreads digit 1 as "l"/"I"/"i" and digit 0 as "O"/"o" inside the numeral,
# e.g. "Pasall" (Pasal 1), "PasallO" (Pasal 10), "Pasall3" (Pasal 13),
# "PasaliOI" (Pasal 101). A pure-uppercase-roman numeral (e.g. "Pasal I",
# "Pasal II" - used for amendment insertion articles) is left untouched; the
# whole-line anchor still keeps in-body references like "Pasal 49 ayat (1)
# huruf a ..." from matching as a heading.
RE_PASAL = re.compile(r"^Pasa[l1]\s*([0-9lIOoiVXLC]+[A-Z]?)\s*$")
RE_AYAT = re.compile(r"^\((\d+[a-z]?)\)")
RE_STOP = re.compile(r"^PENJELASAN\b")
# Ruling B: appendix heading, only honored once a Pasal has been seen.
RE_LAMPIRAN = re.compile(r"^LAMPI\s?RAN\b")
# Amendment laws only: "38. Ketentuan Pasal 50 diubah…", "2. Di antara Pasal 65 dan Pasal 66…".
RE_INSTRUCTION = re.compile(r"^\d+\.\s+(Ketentuan|Di\s*antara|Pasal\s+\S+\s+dihapus)\b")
# Amendment laws only: a whole-pasal deletion instruction, e.g. "18. Ketentuan Pasal 44
# dihapus." Distinct from a sub-item deletion ("b. dihapus.") or a narrative mention
# ("... dinyatakan dihapus."), neither of which names a pasal to strike as a whole.
RE_DIHAPUS = re.compile(r"^\d+\.\s+Ketentuan\s+Pasal\s+(\S+?)\s+dihapus\.?\s*$")

_ROMAN_ONLY = re.compile(r"^[IVXLC]+$")

# Page furniture repeated on every page of the peraturan.go.id / djpp PDFs.
_CHROME_LINES = {"PRESIDEN", "REPUBLIK INDONESIA", "www.djpp.depkumham.go.id", "Agar"}
# OCR variants of the page header and the gazette stamp ("trRESIDEN", "REPUBLIK' INDONESIA",
# "SK No 006?66 A"); none of these is ever legal text.
RE_FUZZY_CHROME = re.compile(r"^(SK No\b.*|\W*\w{0,3}RESIDEN\W*|REPUBLIK\W*\s+INDONESIA\W*)$")
# Editorial footnote ("* Berdasarkan SEMA ...") running up to the next ayat or the end of the body.
RE_FOOTNOTE = re.compile(r"(?ms)^\*\s.*?(?=^\(\s?\d+\)|\Z)")
# Page-turn catchword: the first words of the next page repeated at the page bottom.
RE_CATCHWORD = re.compile(r"(\.\s?\.\s?\.|…)\s*$")
# Enactment formula after the last pasal; everything after it is signatures and gazette data.
RE_CLOSING = re.compile(r"^Agar(\s+supaya)?\s+setiap\s+orang", re.IGNORECASE)

# A digit "1" between two lowercase letters is the letter "l" misread by OCR.
_DIGIT_ONE_IN_WORD = re.compile(r"(?<=[a-z])1(?=[a-z])")
# A reduplicated word glued together by soft-hyphen removal loses its hyphen.
_GLUED_REDUPLICATION = re.compile(r"\b([a-z]{3,})\1(nya|lah|kah)?\b", re.IGNORECASE)


def _is_chrome(line: str) -> bool:
    return (line in _CHROME_LINES or bool(RE_FUZZY_CHROME.match(line))
            or (len(line) <= 60 and bool(RE_CATCHWORD.search(line))))


def _corrector(corrections: dict[str, str]):
    if not corrections:
        return lambda line: line
    words = sorted(corrections, key=len, reverse=True)
    pattern = re.compile(r"\b(" + "|".join(map(re.escape, words)) + r")\b", re.IGNORECASE)

    def fix(match: re.Match) -> str:
        good = corrections[match.group(0).lower()]
        return good[0].upper() + good[1:] if match.group(0)[0].isupper() else good

    def apply(line: str) -> str:
        line = _DIGIT_ONE_IN_WORD.sub("l", line)
        line = _GLUED_REDUPLICATION.sub(r"\1-\1\2", line)
        return pattern.sub(fix, line)

    return apply


def _normalize_numeral(raw: str) -> str:
    return raw.replace("l", "I")


def _normalize_pasal(raw: str) -> str:
    if _ROMAN_ONLY.match(raw):
        return raw
    return raw.translate(str.maketrans("lIOoi", "11001"))


def parse_regulation(text: str, source: Source) -> list[Chunk]:
    chunks: list[Chunk] = []
    seen: dict[str, int] = {}
    buku = bab = bagian = pasal = None
    body: list[str] = []
    seen_pasal = False
    in_instruction = False
    fix_ocr = _corrector(source.text_corrections)
    used: set[str] = set()
    pending: dict[str, str] = {}

    def flush() -> None:
        nonlocal pasal, body
        if pasal is not None:
            content = "\n".join(body).strip()
            for old, new in source.text_replacements.items():
                if old in content:
                    content = content.replace(old, new)
                    used.add(old)
            target = source.footnote_moves.get(pasal)
            if target is not None and (m := RE_FOOTNOTE.search(content)):
                pending[target] = m.group(0).strip()
                content = (content[:m.start()] + content[m.end():]).replace("\n\n", "\n").strip()
            if content:
                chunks.extend(_pasal_chunks(source, buku, bab, bagian, pasal, content, seen))
        pasal, body = None, []

    for raw in text.splitlines():
        line = fix_ocr(raw.strip())
        if not line:
            continue
        if seen_pasal and (RE_STOP.match(line) or RE_LAMPIRAN.match(line)
                           or RE_CLOSING.match(line)):
            break
        if _is_chrome(line):
            continue
        if m := RE_BUKU.match(line):
            flush()
            buku, bab, bagian = _normalize_numeral(m.group(1)), None, None
            in_instruction = False
        elif m := RE_BAB.match(line):
            flush()
            bab, bagian = _normalize_numeral(m.group(1)), None
            in_instruction = False
        elif m := RE_BAGIAN.match(line):
            flush()
            bagian = m.group(1).lower()
            in_instruction = False
        elif m := RE_PASAL.match(line):
            flush()
            pasal = _normalize_pasal(m.group(1))
            seen_pasal = True
            in_instruction = False
        elif pasal is not None:
            if source.amends and RE_INSTRUCTION.match(line):
                in_instruction = True
            if not in_instruction:
                body.append(line)
    flush()
    unused = sorted(set(source.text_replacements) - used)
    if unused:
        raise ValueError(f"{source.doc_id}: text_replacements never matched: {unused}")
    for source_pasal, target in source.footnote_moves.items():
        note = pending.get(target)
        idx = [i for i, c in enumerate(chunks) if c.hierarchy.get("pasal") == target]
        if note is None or not idx:
            raise ValueError(f"{source.doc_id}: footnote of Pasal {source_pasal} "
                             f"not moved to Pasal {target}")
        last = chunks[idx[-1]]
        chunks[idx[-1]] = last.model_copy(update={"text": f"{last.text}\n{note}"})
    return chunks


def _split_ayat(content: str) -> list[tuple[str, str]]:
    parts: list[tuple[str, list[str]]] = []
    preamble: list[str] = []
    expected = 1
    for line in content.splitlines():
        m = RE_AYAT.match(line)
        # Ayat numbers are sequential. A PDF line-wrap can leave a body line
        # that happens to start with "(N)" — e.g. "...dimaksud pada ayat\n(1)
        # berdasarkan panggilan..." — which is a continuation, not a new ayat.
        # Only accept the match when N is the expected next number, else treat
        # the line as body text (avoids duplicate ayat numbers / chunk_ids).
        if m and int(re.match(r"\d+", m.group(1)).group()) == expected:
            lines = (preamble + [line]) if not parts else [line]
            parts.append((m.group(1), lines))
            expected += 1
        elif parts:
            parts[-1][1].append(line)
        else:
            preamble.append(line)
    return [(no, "\n".join(lines).strip()) for no, lines in parts]


def _pasal_chunks(source, buku, bab, bagian, pasal, content, seen) -> list[Chunk]:
    domain = source.resolve_domain(buku, bab)
    if domain == "skip":
        return []
    base_id = f"{source.doc_id}:pasal-{pasal.lower()}"
    seen[base_id] = seen.get(base_id, 0) + 1
    if seen[base_id] > 1:
        base_id = f"{base_id}-{seen[base_id]}"
    hierarchy = {"buku": buku, "bab": bab, "bagian": bagian, "pasal": pasal, "ayat": None}
    ayat_parts = _split_ayat(content)
    if approx_tokens(content) <= MAX_TOKENS or len(ayat_parts) < 2:
        return [_chunk(source, base_id, hierarchy, f"{source.singkatan} Pasal {pasal}",
                       f"Pasal {pasal}\n{content}", domain)]
    return [
        _chunk(source, f"{base_id}:ayat-{no}", {**hierarchy, "ayat": no},
               f"{source.singkatan} Pasal {pasal} ayat ({no})",
               f"Pasal {pasal} ayat ({no})\n{txt}", domain)
        for no, txt in ayat_parts
    ]


def _chunk(source: Source, chunk_id, hierarchy, citation, text, domain) -> Chunk:
    return Chunk(
        chunk_id=chunk_id, doc_id=source.doc_id, doc_title=source.judul,
        source_type="regulation", domain=domain, hierarchy=hierarchy, citation=citation,
        text=text, source_url=source.url_sumber, status=source.status,
        license=source.lisensi, visibility=source.visibility,
    )


def deleted_pasal(text: str) -> set[str]:
    """Whole-pasal deletion instructions in an amendment law's raw text, e.g.
    "18. Ketentuan Pasal 44 dihapus." Returns the deleted base-law pasal numbers."""
    return {
        _normalize_pasal(m.group(1))
        for line in text.splitlines()
        if (m := RE_DIHAPUS.match(line.strip()))
    }


def mark_amendments(
    chunks: list[Chunk],
    sources: dict[str, Source],
    deletions: dict[str, set[str]] | None = None,
) -> list[Chunk]:
    """Flag base-law pasal re-issued or deleted by amendment laws, and cite amendment
    chunks by the base pasal they re-issue. Status/hierarchy come from the LATEST event
    per (base doc, pasal), ordered by the amending Source's `tahun`. `deletions` maps an
    amending doc_id to the (base-law) pasal numbers it deletes (see `deleted_pasal`).
    Chunk ids are unchanged."""
    deletions = deletions or {}
    # events[(base_doc, pasal)] = [(tahun, "reissue" | "delete", amending doc_id), ...]
    events: dict[tuple[str, str], list[tuple[int, str, str]]] = {}
    reissued: dict[tuple[str, str], set[str]] = {}
    for c in chunks:
        src = sources.get(c.doc_id)
        pasal = c.hierarchy.get("pasal")
        if src and src.amends and pasal and not _ROMAN_ONLY.match(pasal):
            reissued.setdefault((src.amends, pasal), set()).add(src.singkatan)
            events.setdefault((src.amends, pasal), []).append(
                (src.tahun or 0, "reissue", src.doc_id))
    for doc_id, deleted in deletions.items():
        src = sources.get(doc_id)
        if not src or not src.amends:
            continue
        for pasal in deleted:
            events.setdefault((src.amends, pasal), []).append((src.tahun or 0, "delete", doc_id))
    bases = {src.amends for src in sources.values() if src.amends}

    def latest(base_doc: str, pasal: str, after: int) -> tuple[int, str, str] | None:
        candidates = [e for e in events.get((base_doc, pasal), []) if e[0] > after]
        return max(candidates, key=lambda e: e[0]) if candidates else None

    def _without_event_keys(hierarchy: dict) -> dict:
        return {k: v for k, v in hierarchy.items() if k not in ("diubah_oleh", "dicabut_oleh")}

    out: list[Chunk] = []
    for c in chunks:
        src = sources.get(c.doc_id)
        pasal = c.hierarchy.get("pasal")
        if c.source_type != "regulation" or src is None or pasal is None:
            out.append(c)
        elif c.doc_id in bases:
            ev = latest(c.doc_id, pasal, after=-1)
            hierarchy = _without_event_keys(c.hierarchy)
            if ev is None:
                out.append(c.model_copy(update={"status": "berlaku", "hierarchy": hierarchy}))
            elif ev[1] == "reissue":
                hierarchy["diubah_oleh"] = ", ".join(sorted(reissued[(c.doc_id, pasal)]))
                out.append(c.model_copy(update={"status": "diubah", "hierarchy": hierarchy}))
            else:
                hierarchy["dicabut_oleh"] = sources[ev[2]].singkatan
                out.append(c.model_copy(update={"status": "dicabut", "hierarchy": hierarchy}))
        elif src.amends and not _ROMAN_ONLY.match(pasal):
            ayat = c.hierarchy.get("ayat")
            citation = (f"{sources[src.amends].singkatan} Pasal {pasal}"
                        f"{f' ayat ({ayat})' if ayat else ''} sebagaimana diubah {src.singkatan}")
            hierarchy = _without_event_keys(c.hierarchy)
            ev = latest(src.amends, pasal, after=src.tahun or 0)
            if ev is None:
                status = "berlaku"
            elif ev[1] == "reissue":
                status = "diubah"
                hierarchy["diubah_oleh"] = sources[ev[2]].singkatan
            else:
                status = "dicabut"
                hierarchy["dicabut_oleh"] = sources[ev[2]].singkatan
            out.append(c.model_copy(update={"citation": citation, "status": status,
                                            "hierarchy": hierarchy}))
        else:
            out.append(c)
    return out
