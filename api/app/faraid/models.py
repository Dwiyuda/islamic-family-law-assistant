"""Skema input/output mesin faraid (spec §7.1, §7.3)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

DISCLAIMER = ("Perhitungan ini informasi umum berdasarkan KHI, bukan nasihat hukum "
              "dan bukan pengganti advokat atau Pengadilan Agama.")


class AhliWaris(BaseModel):
    suami: int = Field(0, ge=0, le=1)
    istri: int = Field(0, ge=0, le=4)
    anak_laki: int = Field(0, ge=0)
    anak_perempuan: int = Field(0, ge=0)
    ayah: int = Field(0, ge=0, le=1)
    ibu: int = Field(0, ge=0, le=1)
    kakek: int = Field(0, ge=0, le=1)
    nenek: int = Field(0, ge=0, le=2)
    saudara_laki_kandung: int = Field(0, ge=0)
    saudara_perempuan_kandung: int = Field(0, ge=0)
    saudara_laki_seayah: int = Field(0, ge=0)
    saudara_perempuan_seayah: int = Field(0, ge=0)
    saudara_seibu: int = Field(0, ge=0)


class Pengganti(BaseModel):
    menggantikan: str            # mis. "anak_laki" (orang tua yang wafat lebih dulu)
    anak_laki: int = Field(0, ge=0)
    anak_perempuan: int = Field(0, ge=0)


class FaraidRequest(BaseModel):
    harta_bersih: int = Field(ge=0)
    pewaris_jenis_kelamin: Literal["L", "P"]
    ahli_waris: AhliWaris
    pengganti: list[Pengganti] = []
    di_luar_cakupan: list[str] = []   # mis. ["dzawil_arham", "janin"]


class BagianWaris(BaseModel):
    ahli_waris: str
    jumlah: int
    bagian_pembilang: int
    bagian_penyebut: int
    nominal: int
    dasar: list[str]
    keterangan: str = ""


class FaraidResult(BaseModel):
    status: Literal["ok", "di_luar_cakupan"]
    bagian: list[BagianWaris] = []
    asal_masalah: int | None = None
    aul_terjadi: bool = False
    radd_terjadi: bool = False
    perlu_verifikasi_ahli: bool = False
    sisa_pembulatan: int = 0
    catatan: list[str] = []
    disclaimer: str = DISCLAIMER
    penjelasan: str | None = None
