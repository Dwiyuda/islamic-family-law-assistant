from app.faraid.models import AhliWaris, FaraidRequest, FaraidResult


def test_ahli_waris_defaults_zero():
    a = AhliWaris()
    assert a.anak_laki == 0 and a.istri == 0 and a.saudara_seibu == 0


def test_request_rejects_negative_and_bad_gender():
    import pydantic
    import pytest
    with pytest.raises(pydantic.ValidationError):
        FaraidRequest(harta_bersih=-1, pewaris_jenis_kelamin="L", ahli_waris=AhliWaris())
    with pytest.raises(pydantic.ValidationError):
        FaraidRequest(harta_bersih=1, pewaris_jenis_kelamin="X", ahli_waris=AhliWaris())


def test_result_has_disclaimer_default():
    r = FaraidResult(status="di_luar_cakupan", asal_masalah=None, aul_terjadi=False,
                     radd_terjadi=False, perlu_verifikasi_ahli=False, sisa_pembulatan=0,
                     catatan=["x"])
    assert "bukan nasihat hukum" in r.disclaimer and r.bagian == []
