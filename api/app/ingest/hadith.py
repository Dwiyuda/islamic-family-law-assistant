from __future__ import annotations

from .models import Chunk, HadithMeta
from .sources import Source

COLLECTIONS: dict[str, tuple[str, str]] = {
    "bukhari": ("Sahih al-Bukhari", "Bukhari"),
    "muslim": ("Sahih Muslim", "Muslim"),
    "abudawud": ("Sunan Abu Dawud", "Abu Dawud"),
    "tirmidhi": ("Jami' at-Tirmidzi", "Tirmidzi"),
    "nasai": ("Sunan an-Nasa'i", "An-Nasa'i"),
    "ibnmajah": ("Sunan Ibnu Majah", "Ibnu Majah"),
}

_DOMAIN_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("kewarisan", ("inherit", "fara'id", "faraid", "wills", "wasaya")),
    ("perceraian", ("divorce", "talaq", "li'an", "khul")),
    ("perkawinan", ("marriage", "nikah", "wedlock", "suckling")),
]
_WEAK = ("da'if", "daif", "dhaif", "munkar", "mawdu", "maudu", "shadh")


def section_domain(name: str) -> str | None:
    lowered = name.lower()
    for domain, keywords in _DOMAIN_KEYWORDS:
        if any(k in lowered for k in keywords):
            return domain
    return None


def normalize_grade(collection: str, grades: list[dict]) -> str:
    if collection in ("bukhari", "muslim"):
        return "sahih"
    if not grades:
        return "tidak_diketahui"
    chosen = next((g for g in grades if g.get("name") == "Al-Albani"), grades[0])
    text = chosen.get("grade", "").lower()
    if any(w in text for w in _WEAK):
        return "dhaif"
    if "sahih" in text:
        return "sahih"
    if "hasan" in text:
        return "hasan"
    return "tidak_diketahui"


def _by_number(edition: dict) -> dict[float, dict]:
    return {float(h["hadithnumber"]): h for h in edition["hadiths"]}


def _fmt(number: float) -> str:
    return str(int(number)) if number == int(number) else str(number).replace(".", "-")


def _abdul_baqi_base(entry: dict) -> str | None:
    """Muslim only: hadith-api's `hadithnumber` for this collection is its own
    flat sequential count (e.g. hadithnumber 4140 = Abdul Baqi no. 1614), not
    lookup-able by users. `arabicnumber` carries the real Abdul Baqi print
    number, as a plain digit string ("1401") or "<base>.<chain-index>"
    ("1400.01".."1400.05") when several isnad-only variants of the same
    hadith share one Abdul Baqi number. Verified against
    data/raw/hadis-muslim-ara.json + hadis-info.json: within the family-law
    subset, all 392 entries carry an arabicnumber, grouping into 113 distinct
    base numbers (up to 21 chain-variants sharing one base), and every group
    agrees on domain/book. For the other five collections hadithnumber ==
    arabicnumber, so this is only needed for muslim.
    """
    raw = entry.get("arabicnumber")
    if raw is None:
        return None
    base = str(raw).split(".")[0]
    return base if base.isdigit() else None


def _make_chunk(
    collection: str, kitab: str, short: str, section: str, domain: str, nomor: str,
    text_ar: str, grades: list[dict], ara: Source,
) -> Chunk:
    return Chunk(
        chunk_id=f"hadith:{collection}:{nomor}", doc_id=f"hadis-{collection}",
        doc_title=kitab, source_type="hadith", domain=domain,
        hierarchy={"kitab_bab": section.strip(), "nomor": nomor},
        citation=f"HR. {short} no. {nomor}", text=text_ar, text_ar=text_ar,
        hadith=HadithMeta(kitab=kitab, nomor=nomor,
                           derajat=normalize_grade(collection, grades)),
        source_url=ara.url_sumber, license=ara.lisensi,
    )


def _parse_muslim(kitab: str, short: str, meta: dict, sections: dict,
                   arabic: dict[float, dict], ara: Source) -> list[Chunk]:
    groups: dict[str, list[dict]] = {}
    for entry in meta["hadiths"]:
        number = float(entry["hadithnumber"])
        section = sections.get(str(entry["reference"]["book"]), "")
        domain = section_domain(section)
        if domain is None or number not in arabic:
            continue
        base = _abdul_baqi_base(entry)
        if base is None:
            continue
        groups.setdefault(base, []).append(entry)

    chunks: list[Chunk] = []
    for base, entries in groups.items():
        texts = [arabic[float(e["hadithnumber"])]["text"].strip() for e in entries]
        texts = [t for t in texts if t]
        if not texts:
            continue
        first = entries[0]
        section = sections.get(str(first["reference"]["book"]), "")
        domain = section_domain(section)
        assert domain is not None  # guaranteed by the filter above
        chunks.append(_make_chunk("muslim", kitab, short, section, domain, base,
                                   "\n\n".join(texts), first.get("grades", []), ara))
    return chunks


def parse_hadith(collection: str, ara_json: dict, info: dict, ara: Source) -> list[Chunk]:
    """Build public hadith chunks: Arabic matn + reference only (spec Sec. 4.1)
    — the six Indonesian hadith editions have unverifiable translation
    provenance/licence (see docs/sources-verification.md), so no translation
    is stored in the public corpus.
    """
    kitab, short = COLLECTIONS[collection]
    meta = info[collection]
    sections = meta["metadata"]["sections"]
    arabic = _by_number(ara_json)

    if collection == "muslim":
        return _parse_muslim(kitab, short, meta, sections, arabic, ara)

    chunks: list[Chunk] = []
    for entry in meta["hadiths"]:
        number = float(entry["hadithnumber"])
        section = sections.get(str(entry["reference"]["book"]), "")
        domain = section_domain(section)
        if domain is None or number not in arabic:
            continue
        text_ar = arabic[number]["text"].strip()
        if not text_ar:
            continue
        nomor = _fmt(number)
        chunks.append(_make_chunk(collection, kitab, short, section, domain, nomor,
                                   text_ar, entry.get("grades", []), ara))
    return chunks
