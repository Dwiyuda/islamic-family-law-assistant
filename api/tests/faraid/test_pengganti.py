from fractions import Fraction

from app.faraid import hitung_faraid
from app.faraid.models import AhliWaris, FaraidRequest, Pengganti


def bagian(res, nama):
    return next((b for b in res.bagian if b.ahli_waris == nama), None)


def frac(res, nama):
    b = bagian(res, nama)
    return Fraction(b.bagian_pembilang, b.bagian_penyebut) if b else Fraction(0)


def test_nenek_seperenam_dan_ditandai():
    r = hitung_faraid(FaraidRequest(harta_bersih=600_000_000, pewaris_jenis_kelamin="L",
                                    ahli_waris=AhliWaris(nenek=1, anak_laki=1)))
    assert (bagian(r, "nenek").bagian_pembilang, bagian(r, "nenek").bagian_penyebut) == (1, 6)
    assert r.perlu_verifikasi_ahli and any("faraid-notes" in c for c in r.catatan)


def test_dua_nenek_berbagi_seperenam():
    r = hitung_faraid(FaraidRequest(harta_bersih=0, pewaris_jenis_kelamin="L",
                                    ahli_waris=AhliWaris(nenek=2, anak_laki=1)))
    assert bagian(r, "nenek").jumlah == 2 and frac(r, "nenek") == Fraction(1, 6)


def test_nenek_terhijab_ibu_tidak_ditandai():
    r = hitung_faraid(FaraidRequest(harta_bersih=0, pewaris_jenis_kelamin="L",
                                    ahli_waris=AhliWaris(ibu=1, nenek=1, anak_laki=1)))
    assert bagian(r, "nenek") is None and not r.perlu_verifikasi_ahli


def test_kakek_seperti_ayah_menghijab_saudara():
    r = hitung_faraid(FaraidRequest(harta_bersih=0, pewaris_jenis_kelamin="L",
                                    ahli_waris=AhliWaris(kakek=1, saudara_laki_kandung=2)))
    assert bagian(r, "saudara_laki_kandung") is None   # terhijab kakek (tafsir)
    assert (bagian(r, "kakek").bagian_pembilang, bagian(r, "kakek").bagian_penyebut) == (1, 1)
    assert r.perlu_verifikasi_ahli


def test_kakek_dengan_keturunan_seperenam_plus_sisa():
    r = hitung_faraid(FaraidRequest(harta_bersih=0, pewaris_jenis_kelamin="L",
                                    ahli_waris=AhliWaris(kakek=1, anak_perempuan=1)))
    assert frac(r, "anak_perempuan") == Fraction(1, 2)
    assert frac(r, "kakek") == Fraction(1, 6) + Fraction(1, 3)


def test_kakek_terhijab_ayah_tidak_ditandai():
    r = hitung_faraid(FaraidRequest(harta_bersih=0, pewaris_jenis_kelamin="L",
                                    ahli_waris=AhliWaris(ayah=1, kakek=1, anak_laki=1)))
    assert bagian(r, "kakek") is None and not r.perlu_verifikasi_ahli


def test_pengganti_cucu_dari_anak_laki_wafat():
    # Pewaris punya 1 anak laki (hidup) + cucu dari anak laki yang wafat (1 cucu laki).
    req = FaraidRequest(harta_bersih=0, pewaris_jenis_kelamin="L",
                        ahli_waris=AhliWaris(anak_laki=1),
                        pengganti=[Pengganti(menggantikan="anak_laki", anak_laki=1)])
    r = hitung_faraid(req)
    assert r.perlu_verifikasi_ahli and any("faraid-notes" in c for c in r.catatan)
    assert frac(r, "pengganti_anak_laki") == Fraction(1, 2)
    assert frac(r, "anak_laki") == Fraction(1, 2)
    assert "khi-1991:pasal-185" in bagian(r, "pengganti_anak_laki").dasar


def test_pengganti_dibagi_dua_banding_satu():
    req = FaraidRequest(harta_bersih=900, pewaris_jenis_kelamin="L",
                        ahli_waris=AhliWaris(anak_laki=1),
                        pengganti=[Pengganti(menggantikan="anak_laki", anak_laki=1,
                                             anak_perempuan=1)])
    r = hitung_faraid(req)
    assert frac(r, "pengganti_anak_laki") == Fraction(1, 2)
    assert sum(b.nominal for b in r.bagian) + r.sisa_pembulatan == 900


def test_pengganti_dibatasi_sederajat():
    # Anak laki wafat (1 cucu laki) + 1 anak perempuan hidup: tanpa batas cucu 2/3 > anak perempuan 1/3.
    # Pasal 185(2): cucu dibatasi = bagian anak perempuan (1/3); selisih 1/3 kembali ke anak perempuan.
    req = FaraidRequest(harta_bersih=0, pewaris_jenis_kelamin="L",
                        ahli_waris=AhliWaris(anak_perempuan=1),
                        pengganti=[Pengganti(menggantikan="anak_laki", anak_laki=1)])
    r = hitung_faraid(req)
    assert frac(r, "pengganti_anak_laki") == Fraction(1, 3)
    assert frac(r, "anak_perempuan") == Fraction(2, 3)
    assert sum(frac(r, b.ahli_waris) for b in r.bagian) == 1
    assert any("185" in c for c in r.catatan)


def test_pengganti_tidak_didukung_di_luar_cakupan():
    r = hitung_faraid(FaraidRequest(harta_bersih=0, pewaris_jenis_kelamin="L",
                                    ahli_waris=AhliWaris(anak_laki=1),
                                    pengganti=[Pengganti(menggantikan="ayah", anak_laki=1)]))
    assert r.status == "di_luar_cakupan"


def test_tanpa_tafsir_tidak_ditandai():
    r = hitung_faraid(FaraidRequest(harta_bersih=0, pewaris_jenis_kelamin="L",
                                    ahli_waris=AhliWaris(anak_laki=1, ibu=1)))
    assert not r.perlu_verifikasi_ahli
