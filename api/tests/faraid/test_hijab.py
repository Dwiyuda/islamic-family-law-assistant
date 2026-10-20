from app.faraid.hijab import terhijab
from app.faraid.models import AhliWaris


def test_anak_laki_menghijab_saudara():
    a = AhliWaris(anak_laki=1, saudara_laki_kandung=1, saudara_seibu=2)
    h = terhijab(a)
    assert "saudara_laki_kandung" in h and "saudara_seibu" in h


def test_ayah_menghijab_saudara_dan_kakek():
    a = AhliWaris(ayah=1, kakek=1, saudara_perempuan_kandung=1)
    h = terhijab(a)
    assert "kakek" in h and "saudara_perempuan_kandung" in h


def test_kandung_menghijab_seayah():
    a = AhliWaris(saudara_laki_kandung=1, saudara_laki_seayah=2)
    assert "saudara_laki_seayah" in terhijab(a)


def test_ibu_menghijab_nenek():
    a = AhliWaris(ibu=1, nenek=1)
    assert "nenek" in terhijab(a)


def test_far_un_warith_perempuan_menghijab_seibu():
    a = AhliWaris(anak_perempuan=1, saudara_seibu=1)
    assert "saudara_seibu" in terhijab(a)


def test_saudari_kandung_tidak_blok_saudara_laki_seayah():
    a = AhliWaris(saudara_perempuan_kandung=1, saudara_laki_seayah=1)
    assert "saudara_laki_seayah" not in terhijab(a)


def test_saudari_kandung_asabah_maal_ghair_blok_seayah():
    a = AhliWaris(anak_perempuan=1, saudara_perempuan_kandung=1, saudara_laki_seayah=1)
    assert "saudara_laki_seayah" in terhijab(a)


def test_anak_perempuan_saja_tidak_blok_saudara_kandung():
    a = AhliWaris(anak_perempuan=1, saudara_laki_kandung=1)
    assert "saudara_laki_kandung" not in terhijab(a)
