"""Penghalang (hijab) ahli waris inti mengikuti KHI Buku II (Pasal 174 ayat 2, 181, 182)."""
from __future__ import annotations

from .models import AhliWaris

SAUDARA = ("saudara_laki_kandung", "saudara_perempuan_kandung",
           "saudara_laki_seayah", "saudara_perempuan_seayah", "saudara_seibu")
SEAYAH = ("saudara_laki_seayah", "saudara_perempuan_seayah")


def ada_keturunan(a: AhliWaris) -> bool:
    return a.anak_laki > 0 or a.anak_perempuan > 0


def terhijab(a: AhliWaris) -> set[str]:
    h: set[str] = set()
    # Saudara (semua) gugur bila ada anak laki atau ayah.
    if a.anak_laki > 0 or a.ayah > 0:
        h.update(SAUDARA)
    # Kakek (ayah tiada) menghijab saudara seperti ayah. TAFSIR PA (faraid-notes.md).
    if a.kakek > 0 and a.ayah == 0:
        h.update(SAUDARA)
    # Saudara seibu gugur bila ada keturunan (anak laki/perempuan) atau ayah.
    if ada_keturunan(a) or a.ayah > 0:
        h.add("saudara_seibu")
    # Seayah terhijab oleh saudara LAKI kandung (selalu), atau saudari kandung yang
    # menjadi asabah ma'al-ghair (bersama anak perempuan, tanpa anak laki & ayah).
    full_sister_asabah = (a.saudara_perempuan_kandung > 0 and a.anak_perempuan > 0
                          and a.anak_laki == 0 and a.ayah == 0)
    if a.saudara_laki_kandung > 0 or full_sister_asabah:
        h.update(SEAYAH)
    # Kakek terhalang ayah; nenek terhalang ibu. Model hanya satu 'nenek' tanpa sisi, jadi
    # "ayah menghalangi nenek pihak ayah" tidak dimodelkan (batasan; lihat faraid-notes.md).
    if a.ayah > 0:
        h.add("kakek")
    if a.ibu > 0:
        h.add("nenek")
    return h
