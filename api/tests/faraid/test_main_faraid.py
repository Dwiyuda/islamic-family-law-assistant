from fastapi.testclient import TestClient

from app.main import create_app


def test_post_faraid_ok():
    client = TestClient(create_app())
    body = {"harta_bersih": 800_000_000, "pewaris_jenis_kelamin": "L",
            "ahli_waris": {"istri": 1, "anak_laki": 1}}
    r = client.post("/faraid", json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    istri = next(b for b in data["bagian"] if b["ahli_waris"] == "istri")
    assert (istri["bagian_pembilang"], istri["bagian_penyebut"]) == (1, 8)
    assert istri["nominal"] == 100_000_000
    assert "bukan nasihat hukum" in data["disclaimer"]


def test_post_faraid_di_luar_cakupan():
    client = TestClient(create_app())
    body = {"harta_bersih": 1, "pewaris_jenis_kelamin": "L",
            "ahli_waris": {"anak_laki": 1}, "di_luar_cakupan": ["dzawil_arham"]}
    assert client.post("/faraid", json=body).json()["status"] == "di_luar_cakupan"


class _FakeProvider:
    name, model = "fake", "fake"

    def __init__(self, text):
        self.text = text

    def complete(self, messages, schema):
        return {"penjelasan": self.text}


_BODY = {"harta_bersih": 800_000_000, "pewaris_jenis_kelamin": "L",
         "ahli_waris": {"istri": 1, "anak_laki": 1}}


def _client_with(provider):
    from app.generation.service import Assistant
    return TestClient(create_app(Assistant({}, provider), points=0))


def test_bare_app_penjelasan_none():
    assert TestClient(create_app()).post("/faraid", json=_BODY).json()["penjelasan"] is None


def test_penjelasan_diisi_llm():
    teks = "Istri mendapat 1/8 bagian, yaitu Rp 100.000.000."
    data = _client_with(_FakeProvider(teks)).post("/faraid", json=_BODY).json()
    assert data["penjelasan"] == teks
    istri = next(b for b in data["bagian"] if b["ahli_waris"] == "istri")
    assert istri["nominal"] == 100_000_000  # angka tetap dari mesin


def test_penjelasan_dengan_angka_karangan_ditolak():
    data = _client_with(_FakeProvider("Istri mendapat 1/6 bagian.")).post("/faraid", json=_BODY).json()
    assert data["penjelasan"] is None


def test_di_luar_cakupan_tanpa_penjelasan():
    body = {**_BODY, "di_luar_cakupan": ["janin"]}
    data = _client_with(_FakeProvider("x")).post("/faraid", json=body).json()
    assert data["status"] == "di_luar_cakupan" and data["penjelasan"] is None
