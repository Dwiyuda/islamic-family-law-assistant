"""'aul (jumlah furudh > 1) dan radd (jumlah < 1 tanpa asabah, Pasal 193).
Tafsir PA: suami/istri tidak menerima radd (dicatat di docs/faraid-notes.md)."""
from __future__ import annotations

from fractions import Fraction

PASANGAN = ("suami", "istri")


def aul(furudh: dict[str, Fraction]) -> tuple[dict[str, Fraction], bool, int]:
    total = sum(furudh.values(), Fraction(0))
    if total <= 1:
        return furudh, False, (total.denominator if furudh else 1)
    skala = {k: v / total for k, v in furudh.items()}
    # asal masalah baru = penyebut gabungan setelah normalisasi
    asal = max((v.denominator for v in skala.values()), default=1)
    return skala, True, asal


def radd(furudh: dict[str, Fraction], ada_asabah: bool,
         sisa: Fraction) -> tuple[dict[str, Fraction], bool]:
    if ada_asabah or sisa <= 0:
        return furudh, False
    penerima = {k: v for k, v in furudh.items() if k not in PASANGAN}
    if not penerima:
        return furudh, False
    basis = sum(penerima.values(), Fraction(0))
    out = dict(furudh)
    for k, v in penerima.items():
        out[k] = v + sisa * v / basis
    return out, True
