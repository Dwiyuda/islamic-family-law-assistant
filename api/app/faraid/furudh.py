"""Bagian tetap dzawil furudh (KHI Pasal 176-182). Mengembalikan Fraction sebelum 'aul/radd.
Kakek dan ayah dihitung di sini hanya 1/6 bila ada keturunan; porsi asabah (sisa) ada di asabah.py.
Penerima asabah murni (anak_laki, ayah/kakek tanpa keturunan, saudara asabah) tidak dihitung di sini."""
from __future__ import annotations

from fractions import Fraction

from .hijab import ada_keturunan
from .models import AhliWaris


def jumlah_saudara_hadir(a: AhliWaris) -> int:
    """Semua saudara di input (untuk hajb ibu ke 1/6: >=2 saudara menurunkan ibu
    walau mereka terhijab ayah/kakek)."""
    return (a.saudara_laki_kandung + a.saudara_perempuan_kandung
            + a.saudara_laki_seayah + a.saudara_perempuan_seayah + a.saudara_seibu)

def furudh(a: AhliWaris, aktif: set[str]) -> dict[str, Fraction]:
    anak = ada_keturunan(a)
    f: dict[str, Fraction] = {}

    if "suami" in aktif:
        f["suami"] = Fraction(1, 4) if anak else Fraction(1, 2)
    if "istri" in aktif:
        f["istri"] = Fraction(1, 8) if anak else Fraction(1, 4)
    if "ibu" in aktif:
        f["ibu"] = Fraction(1, 6) if (anak or jumlah_saudara_hadir(a) >= 2) else Fraction(1, 3)

    # Anak perempuan: furudh hanya bila tanpa anak laki (jika ada anak laki -> asabah bil-ghair).
    if "anak_perempuan" in aktif and a.anak_laki == 0:
        f["anak_perempuan"] = Fraction(1, 2) if a.anak_perempuan == 1 else Fraction(2, 3)

    # Ayah: 1/6 furudh bila ada keturunan (laki/perempuan). Tanpa keturunan -> asabah (Task 5).
    if "ayah" in aktif and anak:
        f["ayah"] = Fraction(1, 6)

    # Kakek (ayah tiada): seperti ayah, 1/6 bila ada keturunan; sisanya asabah. TAFSIR (faraid-notes.md).
    if "kakek" in aktif and anak:
        f["kakek"] = Fraction(1, 6)

    # Nenek (satu atau lebih berbagi rata): 1/6. TAFSIR (faraid-notes.md).
    if "nenek" in aktif:
        f["nenek"] = Fraction(1, 6)

    if "saudara_seibu" in aktif:
        n = a.saudara_seibu
        f["saudara_seibu"] = Fraction(1, 6) if n == 1 else Fraction(1, 3)

    # Saudari kandung: furudh bila tanpa saudara_laki_kandung DAN tanpa anak perempuan
    # (dengan anak perempuan ia jadi asabah ma'al-ghair -> ditangani asabah.py).
    if ("saudara_perempuan_kandung" in aktif and a.saudara_laki_kandung == 0
            and a.anak_perempuan == 0):
        n = a.saudara_perempuan_kandung
        f["saudara_perempuan_kandung"] = Fraction(1, 2) if n == 1 else Fraction(2, 3)
    # Saudari seayah: furudh bila tanpa saudara_laki_seayah.
    if ("saudara_perempuan_seayah" in aktif and a.saudara_laki_seayah == 0
            and a.anak_perempuan == 0):
        n = a.saudara_perempuan_seayah
        kandung = a.saudara_perempuan_kandung if "saudara_perempuan_kandung" in aktif else 0
        if kandung >= 2:
            pass  # saudari kandung ambil 2/3; saudari seayah tidak dapat furudh
        elif kandung == 1:
            f["saudara_perempuan_seayah"] = Fraction(1, 6)  # takmilah -> total 2/3
        else:
            f["saudara_perempuan_seayah"] = Fraction(1, 2) if n == 1 else Fraction(2, 3)

    return f
