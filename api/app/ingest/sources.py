from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator

from .models import Domain, Visibility

Jenis = Literal["uu", "pp", "inpres", "perma", "prosedur", "quran", "hadis", "kitab", "buku"]
Format = Literal["pdf", "html", "json", "txt"]
DomainOrSkip = Literal["perkawinan", "perceraian", "kewarisan", "peradilan", "prosedur", "skip"]


class DomainRule(BaseModel):
    buku: str | None = None
    bab: str | None = None
    domain: DomainOrSkip


class Source(BaseModel):
    doc_id: str = Field(pattern=r"^[a-z0-9-]+$")
    judul: str
    singkatan: str
    jenis: Jenis
    nomor: str | None = None
    tahun: int | None = None
    status: Literal["berlaku", "diubah", "dicabut"] | None = None
    url_sumber: str
    format: Format
    lisensi: str
    visibility: Visibility = "public"
    domain: Domain
    domain_rules: list[DomainRule] = Field(default_factory=list)
    # reference = kept for verification, never chunked
    role: Literal["corpus", "reference"] = "corpus"
    # Whole-word OCR fixes (lowercase misread -> correct word) applied to every line of this
    # document before parsing. Only for documents whose source text is an OCR scan (KHI).
    text_corrections: dict[str, str] = Field(default_factory=dict)
    # Exact substring of a pasal's body (lines joined with "\n", after text_corrections) ->
    # replacement, for OCR damage a word list cannot fix (split words, scrambled lines).
    # Only corrections an official text supports. Every key must match in the document.
    text_replacements: dict[str, str] = Field(default_factory=dict)
    # Pasal whose body holds a "* ..." editorial footnote -> pasal the footnote belongs to.
    footnote_moves: dict[str, str] = Field(default_factory=dict)
    # For an amendment law: doc_id of the law it amends (its numbered pasal re-issue the base's).
    amends: str | None = None
    # Procedure pages: CSS selector of the article body and how to cut it
    # ("step" = one chunk per top-level <li>, "list" = one chunk per top-level list).
    html_selector: str | None = None
    procedure_unit: Literal["step", "list"] = "step"
    # How the raw file is obtained: "http" = plain GET of url_sumber by download.sync;
    # "hadeethenc" = paginated API snapshot written by `python -m app.ingest.hadeethenc`;
    # "manual" = downloaded by the owner (e.g. behind bot protection); download.sync skips it.
    fetcher: Literal["http", "hadeethenc", "manual"] = "http"
    tanggal_unduh: date | None = None
    sha256: str | None = None
    catatan: str | None = None

    @field_validator("text_corrections")
    @classmethod
    def _lowercase_keys(cls, value: dict[str, str]) -> dict[str, str]:
        bad = [k for k in value if k != k.lower()]
        if bad:
            raise ValueError(f"text_corrections keys must be lowercase: {bad}")
        return value

    def resolve_domain(self, buku: str | None, bab: str | None) -> str:
        """First matching rule wins; a rule field set to None matches anything."""
        for rule in self.domain_rules:
            if (rule.buku is None or rule.buku == buku) and (rule.bab is None or rule.bab == bab):
                return rule.domain
        return self.domain


def load_sources(path: Path, *, expect_visibility: Visibility = "public") -> list[Source]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    sources = [Source.model_validate(item) for item in data.get("sources", [])]
    ids = [s.doc_id for s in sources]
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise ValueError(f"duplicate doc_id: {duplicates}")
    wrong = [s.doc_id for s in sources if s.visibility != expect_visibility]
    if wrong:
        raise ValueError(f"visibility must be {expect_visibility}: {wrong}")
    return sources


def save_sources(path: Path, sources: list[Source]) -> None:
    payload = {"sources": [s.model_dump(mode="json", exclude_none=True) for s in sources]}
    path.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False, width=100), encoding="utf-8"
    )


def raw_path(source: Source, raw_dir: Path) -> Path:
    return raw_dir / f"{source.doc_id}.{source.format}"
