"""Response shapes of spec 6.2 (navigator) and 6.4 (Q&A), plus what the LLM must return."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

DISCLAIMER = (
    "Informasi ini bersifat umum, bukan nasihat hukum, dan bukan pengganti advokat. Untuk "
    "perkara Anda, konsultasikan dengan Pos Bantuan Hukum (Posbakum) di Pengadilan Agama "
    "setempat atau dengan advokat.")
REFUSAL_ADVICE = (
    "Dasar hukum untuk pertanyaan ini tidak ditemukan di sumber yang tersedia. Silakan "
    "konsultasikan ke Pos Bantuan Hukum (Posbakum) di Pengadilan Agama setempat.")
OUT_OF_SCOPE_ADVICE = (
    "Pertanyaan ini di luar cakupan asisten, yang hanya membahas hukum keluarga Islam bagi "
    "Muslim di Indonesia (perkawinan, perceraian, kewarisan). Silakan konsultasikan ke "
    "Posbakum atau advokat.")
RETRIEVAL_ONLY_NOTE = (
    "Mode tanpa LLM: berikut pasal dan dalil yang paling relevan dengan pertanyaan Anda. "
    "Ringkasan otomatis tidak tersedia; bacalah sumber di bawah.")

JenisPerkara = Literal["cerai_gugat", "cerai_talak", "lainnya"]
Status = Literal["ok", "ditolak", "di_luar_cakupan"]
Mode = Literal["llm", "retrieval_only"]


class Langkah(BaseModel):
    urutan: int
    judul: str
    uraian: str
    dokumen: list[str] = Field(default_factory=list)
    sitasi: list[str]


class Sumber(BaseModel):
    chunk_id: str
    citation: str
    text: str
    text_ar: str | None = None
    source_type: str
    status: str | None = None
    derajat: str | None = None
    source_url: str
    license: str


class NavigatorDraft(BaseModel):
    status: Literal["ok", "di_luar_cakupan"]
    jenis_perkara: JenisPerkara = "lainnya"
    pengadilan: str = ""
    ringkasan: str = ""
    langkah: list[Langkah] = Field(default_factory=list)
    peringatan: list[str] = Field(default_factory=list)


class AskDraft(BaseModel):
    status: Literal["ok", "di_luar_cakupan"]
    jawaban: str = ""
    sitasi: list[str] = Field(default_factory=list)


class NavigatorResponse(BaseModel):
    status: Status
    jenis_perkara: JenisPerkara | None = None
    pengadilan: str | None = None
    ringkasan: str
    langkah: list[Langkah] = Field(default_factory=list)
    peringatan: list[str] = Field(default_factory=list)
    sumber: list[Sumber] = Field(default_factory=list)
    disclaimer: str = DISCLAIMER
    mode: Mode


class AskResponse(BaseModel):
    status: Status
    jawaban: str
    sitasi: list[str] = Field(default_factory=list)
    peringatan: list[str] = Field(default_factory=list)  # extension of spec 6.4: status/MK notes
    sumber: list[Sumber] = Field(default_factory=list)
    disclaimer: str = DISCLAIMER
    mode: Mode
