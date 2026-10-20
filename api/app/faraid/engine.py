"""Orkestrasi perhitungan faraid (ahli waris inti + kakek/nenek/pengganti yang bertafsir)."""
from __future__ import annotations

import math
from fractions import Fraction

from . import pengganti as peng
from .asabah import asabah
from .furudh import furudh, jumlah_saudara_hadir
from .hijab import ada_keturunan, terhijab
from .models import AhliWaris, BagianWaris, FaraidRequest, FaraidResult
from .normalisasi import aul, radd
from .sources import dasar

NOTES = "docs/faraid-notes.md"


def _hitung_inti(a: AhliWaris) -> tuple[dict[str, Fraction], bool, bool]:
    """Bagian (Fraction dari harta) tiap ahli waris: furudh + asabah, setelah 'aul/radd."""
    hijab = terhijab(a)
    aktif = {n for n, v in a.model_dump().items() if v and n not in hijab}
    f = furudh(a, aktif)

    # Gharrawayn / umariyyatan (KHI Pasal 178 ayat 2)
    if ({"ibu", "ayah"} <= aktif and not ada_keturunan(a)
            and jumlah_saudara_hadir(a) < 2 and ({"suami", "istri"} & aktif)):
        pasangan = f.get("suami", Fraction(0)) + f.get("istri", Fraction(0))
        f["ibu"] = Fraction(1, 3) * (1 - pasangan)

    aul_terjadi = radd_terjadi = False
    asb: dict[str, Fraction] = {}
    total_f = sum(f.values(), Fraction(0))
    if total_f > 1:
        f, aul_terjadi, _ = aul(f)
    else:
        sisa = 1 - total_f
        asb = asabah(a, aktif, sisa)
        if not asb and sisa > 0:
            f, radd_terjadi = radd(f, False, sisa)

    # Gabung dengan penjumlahan: ayah/kakek bisa dapat 1/6 (furudh) + sisa (asabah)
    bagian: dict[str, Fraction] = dict(f)
    for k, v in asb.items():
        bagian[k] = bagian.get(k, Fraction(0)) + v
    return bagian, aul_terjadi, radd_terjadi


def hitung_faraid(req: FaraidRequest) -> FaraidResult:
    if req.di_luar_cakupan:
        return FaraidResult(
            status="di_luar_cakupan",
            catatan=["Di luar cakupan mesin: " + ", ".join(req.di_luar_cakupan)])
    if tak := peng.tak_didukung(req.pengganti):
        return FaraidResult(
            status="di_luar_cakupan",
            catatan=["Ahli waris pengganti untuk posisi ini di luar cakupan mesin: " + ", ".join(tak)])

    a = req.ahli_waris
    jumlah = a.model_dump()
    hypo = peng.hipotetis(a, req.pengganti)
    bagian_abs, aul_terjadi, radd_terjadi = _hitung_inti(hypo)

    grup: dict[str, object] = {}
    catatan: list[str] = []
    if peng.aktif(req.pengganti):
        bagian_abs, grup, c = peng.terapkan(a, hypo, bagian_abs, req.pengganti)
        catatan += c
        catatan.append("Ahli waris pengganti (KHI Pasal 185) adalah tafsir di luar teks literal "
                       f"KHI; perlu verifikasi ahli. Lihat {NOTES}.")
    bagian_abs = {k: v for k, v in bagian_abs.items() if v > 0}
    if "kakek" in bagian_abs:
        catatan.append("Kakek diperlakukan seperti ayah dan menghijab saudara (tafsir di luar "
                       f"teks literal KHI; berbeda dari muqasamah fikih klasik). Lihat {NOTES}.")
    if "nenek" in bagian_abs:
        catatan.append(f"Bagian nenek 1/6 adalah tafsir di luar teks literal KHI. Lihat {NOTES}.")

    asal_masalah = math.lcm(*(v.denominator for v in bagian_abs.values())) if bagian_abs else None

    bagian: list[BagianWaris] = []
    for nama, frac in bagian_abs.items():
        if nama in grup:
            p = grup[nama]
            lk, pr = peng.bagi_anak(p, frac)
            ket = (f"Pengganti {p.menggantikan} yang wafat lebih dulu; dibagi 2:1 "
                   f"(laki-laki {lk.numerator}/{lk.denominator}, perempuan "
                   f"{pr.numerator}/{pr.denominator} dari harta). Tafsir, lihat {NOTES}.")
            jml, dsr = p.anak_laki + p.anak_perempuan, dasar("pengganti")
        else:
            ket, jml, dsr = "", jumlah[nama], dasar(nama)
        bagian.append(BagianWaris(
            ahli_waris=nama, jumlah=jml,
            bagian_pembilang=frac.numerator, bagian_penyebut=frac.denominator,
            nominal=math.floor(frac * req.harta_bersih), dasar=dsr, keterangan=ket))

    return FaraidResult(
        status="ok", bagian=bagian, asal_masalah=asal_masalah,
        aul_terjadi=aul_terjadi, radd_terjadi=radd_terjadi,
        perlu_verifikasi_ahli=bool(catatan),
        sisa_pembulatan=req.harta_bersih - sum(b.nominal for b in bagian), catatan=catatan)
