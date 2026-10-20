from fractions import Fraction

from app.faraid.asabah import asabah
from app.faraid.models import AhliWaris


def aktif(a):
    return {n for n, v in a.model_dump().items() if v}


def test_anak_laki_dan_perempuan_2_banding_1():
    a = AhliWaris(anak_laki=1, anak_perempuan=1)
    r = asabah(a, aktif(a), Fraction(1))  # tanpa furudh lain, sisa=1
    assert r["anak_laki"] == Fraction(2, 3) and r["anak_perempuan"] == Fraction(1, 3)


def test_ayah_ambil_seluruh_sisa_tanpa_keturunan():
    a = AhliWaris(ayah=1, suami=1)   # suami 1/2 furudh -> sisa 1/2
    r = asabah(a, aktif(a), Fraction(1, 2))
    assert r["ayah"] == Fraction(1, 2)


def test_saudara_laki_kandung_asabah():
    a = AhliWaris(saudara_laki_kandung=2)
    r = asabah(a, aktif(a), Fraction(1))
    assert r["saudara_laki_kandung"] == Fraction(1)


def test_asabah_maal_ghair_saudari_kandung():
    # 2 anak perempuan (furudh 2/3 di engine) + 1 saudari kandung -> saudari ambil sisa
    a = AhliWaris(anak_perempuan=2, saudara_perempuan_kandung=1)
    r = asabah(a, aktif(a), Fraction(1, 3))
    assert r["saudara_perempuan_kandung"] == Fraction(1, 3)


def test_asabah_maal_ghair_saudari_seayah():
    a = AhliWaris(anak_perempuan=1, saudara_perempuan_seayah=1)
    r = asabah(a, aktif(a), Fraction(1, 2))
    assert r["saudara_perempuan_seayah"] == Fraction(1, 2)
