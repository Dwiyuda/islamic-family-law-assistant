"""Ahli waris pengganti (KHI Pasal 185) -- TAFSIR di luar teks literal KHI (docs/faraid-notes.md).

Mekanisme: ahli waris yang wafat lebih dulu dihitung seolah hidup (ikut menentukan hijab dan
bagian ahli waris lain); bagiannya diserahkan kepada anak-anaknya (2:1), dibatasi tidak
melebihi bagian ahli waris sederajat yang hidup (Pasal 185 ayat 2)."""
from __future__ import annotations

from fractions import Fraction

from .asabah import _bagi
from .models import AhliWaris, Pengganti

# Ahli waris yang bisa digantikan -> kelompok sederajat (untuk batas ayat 2).
SEDERAJAT: dict[str, tuple[str, ...]] = {
    "anak_laki": ("anak_laki", "anak_perempuan"),
    "anak_perempuan": ("anak_laki", "anak_perempuan"),
    "saudara_laki_kandung": ("saudara_laki_kandung", "saudara_perempuan_kandung"),
    "saudara_perempuan_kandung": ("saudara_laki_kandung", "saudara_perempuan_kandung"),
    "saudara_laki_seayah": ("saudara_laki_seayah", "saudara_perempuan_seayah"),
    "saudara_perempuan_seayah": ("saudara_laki_seayah", "saudara_perempuan_seayah"),
}


def aktif(pengganti: list[Pengganti]) -> list[Pengganti]:
    return [p for p in pengganti if p.anak_laki + p.anak_perempuan > 0]


def tak_didukung(pengganti: list[Pengganti]) -> list[str]:
    return sorted({p.menggantikan for p in aktif(pengganti)} - SEDERAJAT.keys())


def hipotetis(a: AhliWaris, pengganti: list[Pengganti]) -> AhliWaris:
    """Ahli waris yang wafat dihitung seolah hidup."""
    h = a.model_dump()
    for p in aktif(pengganti):
        h[p.menggantikan] += 1
    return AhliWaris(**h)


def terapkan(a: AhliWaris, hypo: AhliWaris, bagian: dict[str, Fraction],
             pengganti: list[Pengganti]) -> tuple[dict[str, Fraction], dict[str, Pengganti], list[str]]:
    """bagian = hasil hitung atas `hypo`. Mengembalikan (bagian akhir, {nama_grup: Pengganti}, catatan)."""
    hc = hypo.model_dump()
    hidup = a.model_dump()
    per = lambda t: bagian.get(t, Fraction(0)) / hc[t] if hc[t] else Fraction(0)  # noqa: E731
    hasil = dict(bagian)
    grup: dict[str, Pengganti] = {}
    catatan: list[str] = []
    kelebihan: list[tuple[tuple[str, ...], Fraction]] = []
    for p in aktif(pengganti):
        t = p.menggantikan
        bagian_ortu = per(t)
        hasil[t] = hasil.get(t, Fraction(0)) - bagian_ortu
        sebaya = [x for x in SEDERAJAT[t] if hidup[x] > 0 and per(x) > 0]
        batas = max((per(x) for x in sebaya), default=None)
        diterima = bagian_ortu
        if batas is not None and bagian_ortu > batas:
            diterima = batas
            kelebihan.append((tuple(sebaya), bagian_ortu - batas))
            catatan.append(f"Bagian pengganti {t} dibatasi tidak melebihi ahli waris sederajat "
                           "(KHI Pasal 185 ayat 2); selisihnya kembali ke ahli waris sederajat "
                           "yang hidup (tafsir, lihat docs/faraid-notes.md).")
        nama = f"pengganti_{t}"
        n = sum(1 for g in grup if g.startswith(nama))
        nama = nama if n == 0 else f"{nama}_{n + 1}"
        grup[nama] = p
        hasil[nama] = diterima
    for sebaya, lebih in kelebihan:
        total = sum(hasil[x] for x in sebaya if x in hasil)
        for x in sebaya:
            if x in hasil:
                hasil[x] += lebih * hasil[x] / total
    return hasil, grup, catatan


def bagi_anak(p: Pengganti, bagian: Fraction) -> tuple[Fraction, Fraction]:
    """Pembagian 2:1 di antara anak pengganti (laki, perempuan) -- total bagian grup `bagian`."""
    return _bagi(p.anak_laki, p.anak_perempuan, bagian)
