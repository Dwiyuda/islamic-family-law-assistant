"""Source ordering (spec 4.4), the weak-source rule, and per-article warnings."""

from __future__ import annotations

from app.ingest.models import Chunk

from .schemas import Sumber

WEAK_GRADES = {"dhaif", "tidak_diketahui"}
WEAK = 5

# Owner-verified on mkri.id (date in docs/sources-verification.md). Not in the corpus:
# these only warn and point to the decision; they never restate its content.
CHUNK_NOTES: dict[str, str] = {
    "uu-1-1974:pasal-43": (
        "Pasal ini telah dimaknai ulang oleh Putusan Mahkamah Konstitusi Nomor "
        "46/PUU-VIII/2010. Baca amar putusannya di mkri.id sebelum memakai pasal ini."),
    "uu-1-1974:pasal-29": (
        "Pasal ini telah dimaknai ulang oleh Putusan Mahkamah Konstitusi Nomor "
        "69/PUU-XIII/2015. Baca amar putusannya di mkri.id sebelum memakai pasal ini."),
}


def authority(chunk: Chunk) -> int:
    """Lower is stronger: regulation, procedure (official court guide), Qur'an, sahih/hasan
    hadith, kitab/book; repealed articles and dhaif/ungraded hadith rank last as WEAK."""
    if chunk.source_type == "regulation":
        return WEAK if chunk.status == "dicabut" else 0
    if chunk.source_type == "procedure":
        return 1
    if chunk.source_type == "quran":
        return 2
    if chunk.source_type == "hadith":
        return WEAK if chunk.hadith.derajat in WEAK_GRADES else 3
    return 4


def is_weak(chunk: Chunk) -> bool:
    """May support a step only together with a stronger source (spec 6.3 rule 2)."""
    return authority(chunk) == WEAK


def order_by_authority(chunk_ids: list[str], chunks: dict[str, Chunk]) -> list[str]:
    # sorted() is stable, so rerank order is kept within a tier
    return sorted(chunk_ids, key=lambda cid: authority(chunks[cid]))


def to_sumber(chunk: Chunk) -> Sumber:
    return Sumber(chunk_id=chunk.chunk_id, citation=chunk.citation, text=chunk.text,
                  text_ar=chunk.text_ar, source_type=chunk.source_type, status=chunk.status,
                  derajat=chunk.hadith.derajat if chunk.hadith else None,
                  source_url=chunk.source_url, license=chunk.license)


def notes_for(chunk_ids: list[str], chunks: dict[str, Chunk]) -> list[str]:
    notes = []
    for cid in chunk_ids:
        chunk = chunks[cid]
        if chunk.status == "diubah":
            notes.append(f"{chunk.citation} telah diubah oleh peraturan yang lebih baru; "
                         "periksa bunyi pasal perubahannya.")
        elif chunk.status == "dicabut":
            notes.append(f"{chunk.citation} sudah dicabut dan tidak berlaku lagi.")
        if cid in CHUNK_NOTES:
            notes.append(CHUNK_NOTES[cid])
    return notes
