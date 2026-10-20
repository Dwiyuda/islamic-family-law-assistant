"""Peta aturan faraid -> chunk_id pasal KHI (spec §7.2). Tidak ada aturan dari ingatan;
tiap chunk_id wajib ada di korpus (diuji)."""
from __future__ import annotations

K = "khi-1991:pasal-"

DASAR: dict[str, list[str]] = {
    "daftar_ahli_waris": [K + "174"],
    "anak_perempuan": [K + "176"],
    "anak_laki": [K + "176"],
    "ayah": [K + "177"],
    "ibu": [K + "178"],
    "suami": [K + "179"],
    "istri": [K + "180"],
    "saudara_seibu": [K + "181"],
    "saudara_kandung": [K + "182"],
    "saudara_seayah": [K + "182"],
    "radd": [K + "193"],
    # Tafsir di luar teks literal KHI (lihat docs/faraid-notes.md):
    "nenek": [K + "174"],        # hanya disebut di 174; bagian 1/6 = tafsir PA
    "kakek": [K + "174"],        # hanya disebut di 174; diperlakukan seperti ayah = tafsir PA
    "pengganti": [K + "185"],    # Pasal 185 hanya prinsip; mekanisme = tafsir PA
}


def dasar(nama: str) -> list[str]:
    return DASAR.get(nama, [])
