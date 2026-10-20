from fractions import Fraction

from app.faraid.furudh import furudh
from app.faraid.hijab import terhijab
from app.faraid.models import AhliWaris


def aktif(a):
    h = terhijab(a)
    return {n for n, v in a.model_dump().items() if v and n not in h}


def test_suami_separuh_tanpa_anak():
    a = AhliWaris(suami=1, saudara_perempuan_kandung=1)
    assert furudh(a, aktif(a))["suami"] == Fraction(1, 2)


def test_istri_seperdelapan_dengan_anak():
    a = AhliWaris(istri=1, anak_laki=1)
    assert furudh(a, aktif(a))["istri"] == Fraction(1, 8)


def test_dua_anak_perempuan_dua_pertiga():
    a = AhliWaris(anak_perempuan=2, ibu=1)
    f = furudh(a, aktif(a))
    assert f["anak_perempuan"] == Fraction(2, 3) and f["ibu"] == Fraction(1, 6)


def test_ibu_sepertiga_tanpa_anak_tanpa_dua_saudara():
    a = AhliWaris(ibu=1, ayah=1)
    assert furudh(a, aktif(a))["ibu"] == Fraction(1, 3)


def test_dua_saudari_seibu_sepertiga():
    a = AhliWaris(saudara_seibu=2, suami=1)
    assert furudh(a, aktif(a))["saudara_seibu"] == Fraction(1, 3)


def test_satu_saudari_kandung_separuh():
    a = AhliWaris(saudara_perempuan_kandung=1, suami=1)
    assert furudh(a, aktif(a))["saudara_perempuan_kandung"] == Fraction(1, 2)


def test_takmilah_saudari_seayah_seperenam():
    a = AhliWaris(suami=1, saudara_perempuan_kandung=1, saudara_perempuan_seayah=1)
    f = furudh(a, aktif(a))
    assert f["saudara_perempuan_kandung"] == Fraction(1, 2)
    assert f["saudara_perempuan_seayah"] == Fraction(1, 6)


def test_dua_saudari_kandung_seayah_tak_dapat_furudh():
    a = AhliWaris(suami=1, saudara_perempuan_kandung=2, saudara_perempuan_seayah=1)
    f = furudh(a, aktif(a))
    assert f["saudara_perempuan_kandung"] == Fraction(2, 3)
    assert "saudara_perempuan_seayah" not in f


def test_saudari_kandung_tanpa_furudh_bila_ada_anak_perempuan():
    # anak perempuan + saudari kandung -> saudari jadi asabah ma'al-ghair, tak dapat furudh
    a = AhliWaris(anak_perempuan=1, saudara_perempuan_kandung=1)
    f = furudh(a, aktif(a))
    assert "saudara_perempuan_kandung" not in f
    assert f["anak_perempuan"] == Fraction(1, 2)
