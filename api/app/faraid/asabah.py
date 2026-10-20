"""Ashabah: pembagian sisa (1 - furudh) dengan 2:1 (Pasal 176, 182)."""
from __future__ import annotations

from fractions import Fraction

from .models import AhliWaris


def _bagi(laki: int, perempuan: int, sisa: Fraction) -> tuple[Fraction, Fraction]:
    unit = 2 * laki + perempuan
    if unit == 0:
        return Fraction(0), Fraction(0)
    return sisa * 2 * laki / unit, sisa * perempuan / unit


def asabah(a: AhliWaris, aktif: set[str], sisa: Fraction) -> dict[str, Fraction]:
    if sisa <= 0:
        return {}
    r: dict[str, Fraction] = {}
    if "anak_laki" in aktif and a.anak_laki > 0:
        lk, p = _bagi(a.anak_laki, a.anak_perempuan if "anak_perempuan" in aktif else 0, sisa)
        r["anak_laki"] = lk
        if p:
            r["anak_perempuan"] = p
        return r
    if "ayah" in aktif and a.ayah > 0:
        r["ayah"] = sisa          # sisa setelah furudh lain (1/6 ayah sudah di furudh bila ada keturunan)
        return r
    if "kakek" in aktif and a.kakek > 0:
        r["kakek"] = sisa         # tafsir: kakek seperti ayah (Task 8 menandai)
        return r
    # Asabah ma'al-ghair: saudari kandung/seayah jadi asabah (ambil sisa) bila bersama
    # anak perempuan. Saudara laki dicek per kelas: kandung hanya menghalangi saudari kandung,
    # seayah hanya menghalangi saudari seayah. (anak laki/ayah/kakek sudah return di atas.)
    if a.anak_perempuan > 0:
        if ("saudara_perempuan_kandung" in aktif and a.saudara_perempuan_kandung > 0
                and a.saudara_laki_kandung == 0):
            r["saudara_perempuan_kandung"] = sisa
            return r
        if ("saudara_perempuan_seayah" in aktif and a.saudara_perempuan_seayah > 0
                and a.saudara_laki_seayah == 0):
            r["saudara_perempuan_seayah"] = sisa
            return r
    if ("saudara_laki_kandung" in aktif and a.saudara_laki_kandung > 0):
        lk, p = _bagi(a.saudara_laki_kandung,
                      a.saudara_perempuan_kandung if "saudara_perempuan_kandung" in aktif else 0, sisa)
        r["saudara_laki_kandung"] = lk
        if p:
            r["saudara_perempuan_kandung"] = p
        return r
    if ("saudara_laki_seayah" in aktif and a.saudara_laki_seayah > 0):
        lk, p = _bagi(a.saudara_laki_seayah,
                      a.saudara_perempuan_seayah if "saudara_perempuan_seayah" in aktif else 0, sisa)
        r["saudara_laki_seayah"] = lk
        if p:
            r["saudara_perempuan_seayah"] = p
    return r
