from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

SourceType = Literal["regulation", "procedure", "quran", "hadith", "kitab", "book"]
Domain = Literal["perkawinan", "perceraian", "kewarisan", "peradilan", "prosedur"]
Visibility = Literal["public", "private"]
HadithGrade = Literal["sahih", "hasan", "dhaif", "tidak_diketahui"]

MAX_TOKENS = 350


def approx_tokens(text: str) -> int:
    """Cheap token estimate: whitespace words * 1.3."""
    return int(len(text.split()) * 1.3)


class HadithMeta(BaseModel):
    kitab: str
    nomor: str
    perawi: str | None = None
    derajat: HadithGrade


class Chunk(BaseModel):
    chunk_id: str = Field(pattern=r"^[a-z0-9-]+(:[a-z0-9-]+)*$")
    doc_id: str
    doc_title: str
    source_type: SourceType
    domain: Domain
    hierarchy: dict[str, str | None] = Field(default_factory=dict)
    citation: str
    text: str = Field(min_length=1)
    text_ar: str | None = None
    hadith: HadithMeta | None = None
    source_url: str
    status: str | None = None
    license: str
    visibility: Visibility = "public"

    @model_validator(mode="after")
    def _hadith_meta_matches_type(self) -> Chunk:
        if (self.source_type == "hadith") != (self.hadith is not None):
            raise ValueError("hadith metadata is required for hadith chunks and forbidden otherwise")
        return self
