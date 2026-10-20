from app.faraid import hitung_faraid
from app.faraid.models import AhliWaris, FaraidRequest


def req(hb=0, jk="L", **kw):
    return FaraidRequest(harta_bersih=hb, pewaris_jenis_kelamin=jk, ahli_waris=AhliWaris(**kw))


def bagian(res, nama):
    for b in res.bagian:
        if b.ahli_waris == nama:
            return b
    return None


def test_istri_dan_anak_laki():
    r = hitung_faraid(req(hb=800_000_000, istri=1, anak_laki=1))
    assert r.status == "ok"
    assert (bagian(r, "istri").bagian_pembilang, bagian(r, "istri").bagian_penyebut) == (1, 8)
    assert bagian(r, "istri").nominal == 100_000_000
    assert bagian(r, "anak_laki").nominal == 700_000_000


def test_aul_6_jadi_7_engine():
    r = hitung_faraid(req(jk="P", suami=1, saudara_perempuan_kandung=1, saudara_seibu=1))
    assert r.aul_terjadi and bagian(r, "suami").bagian_penyebut == 7


def test_radd_ibu_dan_anak_perempuan():
    r = hitung_faraid(req(anak_perempuan=1, ibu=1))
    assert r.radd_terjadi
    assert (bagian(r, "anak_perempuan").bagian_pembilang,
            bagian(r, "anak_perempuan").bagian_penyebut) == (3, 4)


def test_gharrawayn_ibu_sepertiga_sisa():
    # suami 1/2, ibu 1/3 sisa = 1/6, ayah sisa. (asal masalah 6: suami 3, ibu 1, ayah 2)
    r = hitung_faraid(req(suami=1, ibu=1, ayah=1))
    assert (bagian(r, "ibu").bagian_pembilang, bagian(r, "ibu").bagian_penyebut) == (1, 6)
    assert (bagian(r, "suami").bagian_pembilang, bagian(r, "suami").bagian_penyebut) == (1, 2)
    assert (bagian(r, "ayah").bagian_pembilang, bagian(r, "ayah").bagian_penyebut) == (1, 3)


def test_di_luar_cakupan():
    req_ = FaraidRequest(harta_bersih=1, pewaris_jenis_kelamin="L",
                         ahli_waris=AhliWaris(anak_laki=1), di_luar_cakupan=["janin"])
    assert hitung_faraid(req_).status == "di_luar_cakupan"


def test_ayah_seperenam_plus_sisa_dengan_anak_perempuan():
    r = hitung_faraid(req(anak_perempuan=1, ayah=1, ibu=1))
    # daughter 1/2, ibu 1/6, ayah 1/6 furudh + 1/6 sisa = 1/3
    assert (bagian(r, "ayah").bagian_pembilang, bagian(r, "ayah").bagian_penyebut) == (1, 3)
    assert (bagian(r, "anak_perempuan").bagian_pembilang, bagian(r, "anak_perempuan").bagian_penyebut) == (1, 2)
    assert (bagian(r, "ibu").bagian_pembilang, bagian(r, "ibu").bagian_penyebut) == (1, 6)


def test_ibu_seperenam_oleh_saudara_terhijab_ayah():
    r = hitung_faraid(req(ayah=1, ibu=1, saudara_laki_kandung=2))
    assert (bagian(r, "ibu").bagian_pembilang, bagian(r, "ibu").bagian_penyebut) == (1, 6)
    assert (bagian(r, "ayah").bagian_pembilang, bagian(r, "ayah").bagian_penyebut) == (5, 6)


def test_bukan_gharrawayn_bila_dua_saudara_terhijab():
    r = hitung_faraid(req(jk="P", suami=1, ibu=1, ayah=1, saudara_laki_kandung=2))
    assert (bagian(r, "suami").bagian_pembilang, bagian(r, "suami").bagian_penyebut) == (1, 2)
    assert (bagian(r, "ibu").bagian_pembilang, bagian(r, "ibu").bagian_penyebut) == (1, 6)
    assert (bagian(r, "ayah").bagian_pembilang, bagian(r, "ayah").bagian_penyebut) == (1, 3)


def test_maal_ghair_saudari_kandung_dengan_saudara_laki_seayah():
    r = hitung_faraid(req(anak_perempuan=1, saudara_perempuan_kandung=1, saudara_laki_seayah=1))
    assert (bagian(r, "anak_perempuan").bagian_pembilang, bagian(r, "anak_perempuan").bagian_penyebut) == (1, 2)
    assert (bagian(r, "saudara_perempuan_kandung").bagian_pembilang, bagian(r, "saudara_perempuan_kandung").bagian_penyebut) == (1, 2)
    assert bagian(r, "saudara_laki_seayah") is None


def test_maal_ghair_dua_anak_perempuan_saudari_kandung_seayah_laki():
    r = hitung_faraid(req(anak_perempuan=2, saudara_perempuan_kandung=1, saudara_laki_seayah=1))
    assert (bagian(r, "anak_perempuan").bagian_pembilang, bagian(r, "anak_perempuan").bagian_penyebut) == (2, 3)
    assert (bagian(r, "saudara_perempuan_kandung").bagian_pembilang, bagian(r, "saudara_perempuan_kandung").bagian_penyebut) == (1, 3)


def test_maal_ghair_saudari_kandung_dan_seayah_dengan_seayah_laki():
    r = hitung_faraid(req(anak_perempuan=1, saudara_perempuan_kandung=1, saudara_perempuan_seayah=1, saudara_laki_seayah=1))
    assert (bagian(r, "anak_perempuan").bagian_pembilang, bagian(r, "anak_perempuan").bagian_penyebut) == (1, 2)
    assert (bagian(r, "saudara_perempuan_kandung").bagian_pembilang, bagian(r, "saudara_perempuan_kandung").bagian_penyebut) == (1, 2)
