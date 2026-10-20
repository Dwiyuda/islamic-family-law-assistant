from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path

import httpx

from .download import USER_AGENT, sha256_file
from .hadith import normalize_grade
from .models import Chunk, HadithMeta
from .sources import Source, load_sources, raw_path, save_sources

API = "https://hadeethenc.com/api/v1"
# HadeethEnc category id -> corpus domain. Order matters: a hadith listed under several
# categories takes the first match (kewarisan > perceraian > perkawinan, as in hadith.py).
CATEGORY_DOMAINS: dict[str, str] = {
    "123": "kewarisan", "166": "kewarisan",
    "192": "perceraian", "193": "perceraian", "194": "perceraian", "195": "perceraian",
    "196": "perceraian", "197": "perceraian", "198": "perceraian", "200": "perceraian",
    "191": "perkawinan", "199": "perkawinan", "201": "perkawinan", "605": "perkawinan",
    "610": "perkawinan",
}
# Narrator at the start of the intro or the hadith text. Tried in order; None if absent.
_PERAWI_PATTERNS = (
    re.compile(r"^(?:Dari\s+)?(.{2,60}?)\s+-\s?ra[ḍd]iyall", re.IGNORECASE),
    # lookahead keeps the terminator in the remainder; "\s+bahwa" also covers "bahwasannya"
    re.compile(r"^Dari\s+(.{2,60}?)(?=,|:|\s+(?:ia|dia)\s+berkata|\s+bahwa)", re.IGNORECASE),
    re.compile(r"^(.{2,60}?)\s+meriwayatkan\b", re.IGNORECASE),
)
# The first matching pattern decides; precision over recall, so a doubtful capture is None.
_BAD_CAPTURE = re.compile(r"berkata|Rasulullah|Nabi|\s+dan\s+|[,\"“”]", re.IGNORECASE)
# Chain: the captured name is a tabi'i and the Companion follows ("dari bapaknya", "dari X").
_CHAIN = re.compile(r"^,?\s*dari\s+(?:bapak|ayah|kakek)", re.IGNORECASE)
_CHAIN_NAME = re.compile(r"^,\s*dari\s+([A-Z'‘’Ā-ž])")
# "Dari X, bahwasannya dia berkata" is a Companion in most entries; these two are tabi'in
# (flagged by the reviewer), so there is no safe general rule. The list is only valid for
# the snapshot fetched 2026-09-27; a re-snapshot needs a new narrator audit.
_TABIIN = {"Ibnu Syihāb", "Abu Salamah bin Abdirrahman"}


def _perawi(*candidates: str | None) -> str | None:
    for text in candidates:
        text = (text or "").strip()
        for pattern in _PERAWI_PATTERNS:
            if m := pattern.match(text):
                name, rest = m.group(1).strip(), text[m.end():]
                if _BAD_CAPTURE.search(name) or name in _TABIIN or _CHAIN.match(rest):
                    return None
                if (c := _CHAIN_NAME.match(rest)) and (c.group(1).isupper() or c.group(1) in "'‘’"):
                    return None
                return name
    return None


def fetch_snapshot(client: httpx.Client, language: str = "id") -> dict:
    assigned: dict[str, tuple[str, str]] = {}
    for category, domain in CATEGORY_DOMAINS.items():
        page = 1
        while True:
            response = client.get(f"{API}/hadeeths/list/", params={
                "language": language, "category_id": category, "page": page, "per_page": 100})
            response.raise_for_status()
            body = response.json()
            for item in body["data"]:
                assigned.setdefault(str(item["id"]), (category, domain))
            if int(body["meta"]["current_page"]) >= int(body["meta"]["last_page"]):
                break
            page += 1
    hadeeths = []
    for hid in sorted(assigned, key=int):
        response = client.get(f"{API}/hadeeths/one/", params={"language": language, "id": hid})
        response.raise_for_status()
        category, domain = assigned[hid]
        hadeeths.append({**response.json(), "_category": category, "_domain": domain})
    return {"api": API, "language": language, "fetched": date.today().isoformat(),
            "hadeeths": hadeeths}


def parse_hadeethenc(snapshot: dict, source: Source) -> list[Chunk]:
    """Indonesian HadeethEnc translation + explanation + lessons, verbatim (terms forbid
    modification or deletion)."""
    chunks: list[Chunk] = []
    for entry in snapshot["hadeeths"]:
        text = (entry.get("hadeeth") or "").strip()
        if not text:
            continue
        explanation = (entry.get("explanation") or "").strip()
        if explanation:
            text = f"{text}\n\nPenjelasan: {explanation}"
        hints = [x.strip() for x in (entry.get("hints") or []) if x and x.strip()]
        if hints:
            text = text + "\n\nPelajaran:\n" + "\n".join(hints)
        nomor = str(entry["id"])
        attribution = (entry.get("attribution") or "").strip() or "HadeethEnc"
        chunks.append(Chunk(
            chunk_id=f"hadith:hadeethenc:{nomor}", doc_id=source.doc_id, doc_title=source.judul,
            source_type="hadith", domain=entry["_domain"],
            hierarchy={"kategori": entry["_category"], "atribusi": attribution, "nomor": nomor},
            citation=f"{attribution} (HadeethEnc no. {nomor})", text=text,
            text_ar=(entry.get("hadeeth_ar") or "").strip() or None,
            hadith=HadithMeta(
                kitab=attribution, nomor=nomor, perawi=_perawi(entry.get("hadeeth_intro"), entry.get("hadeeth")),
                derajat=normalize_grade("hadeethenc",
                                        [{"name": "HadeethEnc", "grade": entry.get("grade") or ""}]),
            ),
            source_url=f"https://hadeethenc.com/id/browse/hadith/{nomor}",
            license=f"{source.lisensi}; versi {snapshot['fetched']}",
            visibility=source.visibility,
        ))
    return chunks


def main() -> None:
    parser = argparse.ArgumentParser(description="Snapshot HadeethEnc family-law hadith")
    parser.add_argument("--data-dir", type=Path, default=Path("../data"))
    args = parser.parse_args()
    manifest = args.data_dir / "sources.yaml"
    sources = load_sources(manifest)
    source = next(s for s in sources if s.fetcher == "hadeethenc")
    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=60) as client:
        snapshot = fetch_snapshot(client)
    target = raw_path(source, args.data_dir / "raw")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(snapshot, ensure_ascii=False, indent=1), encoding="utf-8")
    source.sha256, source.tanggal_unduh = sha256_file(target), date.today()
    save_sources(manifest, sources)
    print(json.dumps({"hadeeths": len(snapshot["hadeeths"]), "file": str(target)}))


if __name__ == "__main__":
    main()
