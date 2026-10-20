import pytest
from fastapi.testclient import TestClient

from app.generation.fakes import FakeProvider
from app.generation.service import Assistant
from app.main import create_app

ASK = {"status": "ok", "jawaban": "Anak perempuan tunggal mendapat separoh.",
       "sitasi": ["khi-1991:pasal-176"]}
ASK_Q = {"pertanyaan": "berapa bagian anak perempuan kalau hanya seorang"}
NAV_Q = {"pertanyaan": "Suami melanggar taklik talak, saya ingin cerai"}


@pytest.fixture
def client(retriever):
    assistant = Assistant(retriever.chunks, FakeProvider(ASK), retriever.search, threshold=0.1)
    with TestClient(create_app(assistant, points=5)) as c:
        yield c


def test_health(client):
    assert client.get("/health").json() == {"status": "ok", "chunks": 5, "index_points": 5,
                                            "mode": "llm", "llm": "fake/fake"}


def test_ask(client):
    r = client.post("/ask", json=ASK_Q)
    body = r.json()
    assert r.status_code == 200 and body["status"] == "ok" and body["mode"] == "llm"
    assert body["sitasi"] == ["khi-1991:pasal-176"] and "advokat" in body["disclaimer"]


def test_navigator_shape(client):
    # FakeProvider returns an Ask-shaped reply: it validates as a navigator draft with no
    # steps, so the guard refuses; the endpoint must still answer with the spec 6.2 keys.
    r = client.post("/navigator", json=NAV_Q)
    assert r.status_code == 200
    assert set(r.json()) == {"status", "jenis_perkara", "pengadilan", "ringkasan", "langkah",
                             "peringatan", "sumber", "disclaimer", "mode"}
    assert (r.json()["status"], r.json()["mode"]) == ("ditolak", "llm")


def test_documents(client):
    assert client.get("/documents/khi-1991:pasal-116").json()["citation"] == "KHI Pasal 116"
    assert client.get("/documents/khi-1991:pasal-999").status_code == 404


def test_question_validation(client):
    assert client.post("/ask", json={"pertanyaan": "a"}).status_code == 422


def test_cors_header_untuk_origin_diizinkan(client):
    r = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"
