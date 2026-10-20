from fractions import Fraction

from app.faraid.normalisasi import aul, radd


def test_aul_6_jadi_7():
    # suami 1/2, saudari kandung 1/2, saudara seibu 1/6 -> 7/6 -> aul 6->7
    f = {"suami": Fraction(1, 2), "saudara_perempuan_kandung": Fraction(1, 2),
         "saudara_seibu": Fraction(1, 6)}
    out, terjadi, asal = aul(f)
    assert terjadi and asal == 7
    assert out["suami"] == Fraction(3, 7) and out["saudara_seibu"] == Fraction(1, 7)


def test_tanpa_aul():
    f = {"suami": Fraction(1, 4), "anak_perempuan": Fraction(1, 2)}
    out, terjadi, asal = aul(f)
    assert not terjadi and out == f


def test_radd_ke_anak_perempuan_dan_ibu():
    # anak perempuan 1/2 + ibu 1/6 = 4/6; sisa 2/6 di-radd proporsional
    f = {"anak_perempuan": Fraction(1, 2), "ibu": Fraction(1, 6)}
    out, terjadi = radd(f, ada_asabah=False, sisa=Fraction(1, 3))
    assert terjadi
    assert out["anak_perempuan"] == Fraction(3, 4) and out["ibu"] == Fraction(1, 4)


def test_radd_tidak_ke_pasangan():
    # istri 1/8 + anak perempuan 1/2 = 5/8; sisa 3/8 hanya ke anak perempuan
    f = {"istri": Fraction(1, 8), "anak_perempuan": Fraction(1, 2)}
    out, terjadi = radd(f, ada_asabah=False, sisa=Fraction(3, 8))
    assert out["istri"] == Fraction(1, 8) and out["anak_perempuan"] == Fraction(7, 8)
