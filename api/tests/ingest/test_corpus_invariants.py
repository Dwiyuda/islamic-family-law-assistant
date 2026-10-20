import json
import re
from collections import Counter
from pathlib import Path

from app.ingest.jsonl import read_chunks

DATA = Path(__file__).resolve().parents[3] / "data" / "processed"

CITATION = {
    "regulation": re.compile(
        r"^\S.* Pasal [0-9IVX]+[A-Z]?( ayat \(\d+[a-z]?\))?( sebagaimana diubah \S.*)?$"
    ),
    "quran": re.compile(r"^QS [A-Z][A-Za-z'-]+ \[\d{1,3}\]: \d{1,3}(-\d{1,3})?$"),
    "hadith": re.compile(r"^(HR\. .+ no\. \d+(-\d+)?|.+ \(HadeethEnc no\. \d+\))$"),
    "procedure": re.compile(r"^\S.*,? (langkah|bagian) \d+$"),
}


def _chunks():
    return read_chunks(DATA / "chunks.jsonl")


def test_ids_unique_and_no_duplicate_pasal_suffix():
    ids = [c.chunk_id for c in _chunks()]
    assert len(ids) == len(set(ids))
    # parse_regulation appends "-2", "-3" when a pasal number repeats: always a parser miss.
    assert [i for i in ids if re.search(r":pasal-[0-9]+[a-z]?-\d+(:|$)", i)] == []


def test_citation_format_per_source_type():
    bad = [
        (c.chunk_id, c.citation)
        for c in _chunks()
        if c.source_type in CITATION and not CITATION[c.source_type].match(c.citation)
    ]
    assert bad == []


def test_text_hygiene_and_visibility():
    chunks = _chunks()
    assert [c.chunk_id for c in chunks if "­" in c.text] == []
    assert {c.visibility for c in chunks} == {"public"}


def test_stats_match_corpus():
    chunks = _chunks()
    stats = json.loads((DATA / "stats.json").read_text(encoding="utf-8"))
    assert stats["total"] == len(chunks) >= 1000
    assert stats["by_doc"] == dict(Counter(c.doc_id for c in chunks))


# A re-snapshot of HadeethEnc must fail this test and force a new narrator audit: the
# _TABIIN list and the extraction rules in app/ingest/hadeethenc.py were audited against
# the snapshot fetched 2026-09-27 (115 of 128 entries name a narrator).
HADEETHENC_WITHOUT_PERAWI = {
    "hadith:hadeethenc:5922", "hadith:hadeethenc:58156", "hadith:hadeethenc:58183",
    "hadith:hadeethenc:58190", "hadith:hadeethenc:58065", "hadith:hadeethenc:58075",
    "hadith:hadeethenc:58082", "hadith:hadeethenc:58103", "hadith:hadeethenc:58106",
    "hadith:hadeethenc:58129", "hadith:hadeethenc:58147", "hadith:hadeethenc:58157",
    "hadith:hadeethenc:58167",
}


def test_hadeethenc_narrator_coverage_is_pinned():
    chunks = [c for c in _chunks() if c.doc_id == "hadeethenc-id"]
    assert len(chunks) == 128
    assert sum(c.hadith.perawi is not None for c in chunks) == 115
    assert {c.chunk_id for c in chunks if c.hadith.perawi is None} == HADEETHENC_WITHOUT_PERAWI
