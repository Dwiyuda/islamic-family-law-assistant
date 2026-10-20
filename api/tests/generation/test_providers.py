import json
import os

import httpx
import pytest

from app.config import load_env_file
from app.generation.providers import (
    OpenAICompatProvider,
    ProviderError,
    ProviderUnavailable,
    make_provider,
)
from app.generation.schemas import AskDraft

MSGS = [{"role": "user", "content": "hai"}]
GOOD = '{"status": "ok", "jawaban": "x", "sitasi": ["a:b"]}'


def _ok(content):
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def _provider(responses, sleeps):
    seen = []

    def handler(request):
        seen.append(request)
        item = responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    client = httpx.Client(transport=httpx.MockTransport(handler), base_url="https://llm.test/v1")
    p = OpenAICompatProvider("groq", "m", "k", "https://llm.test/v1", client=client,
                             sleep=sleeps.append)
    return p, seen


def test_success_validates_and_sends_json_mode():
    p, seen = _provider([_ok(GOOD)], [])
    assert p.complete(MSGS, AskDraft) == {"status": "ok", "jawaban": "x", "sitasi": ["a:b"]}
    req = seen[0]
    body = json.loads(req.content)
    assert req.url.path == "/v1/chat/completions"
    assert req.headers["Authorization"] == "Bearer k"
    assert body["model"] == "m" and body["response_format"] == {"type": "json_object"}
    assert body["temperature"] == 0


def test_retries_rate_limits_and_server_errors():
    sleeps = []
    p, seen = _provider([httpx.Response(429, headers={"retry-after": "7"}),
                         httpx.Response(503), _ok(GOOD)], sleeps)
    assert p.complete(MSGS, AskDraft)["jawaban"] == "x"
    assert sleeps == [7.0, 4.0] and len(seen) == 3


def test_network_error_is_retried():
    sleeps = []
    p, _ = _provider([httpx.ConnectError("down"), _ok(GOOD)], sleeps)
    assert p.complete(MSGS, AskDraft)["status"] == "ok" and sleeps == [2.0]


def test_gives_up_after_three_retries_raises_unavailable():
    sleeps = []
    p, seen = _provider([httpx.Response(429) for _ in range(4)], sleeps)
    with pytest.raises(ProviderUnavailable):
        p.complete(MSGS, AskDraft)
    assert len(seen) == 4 and sleeps == [2.0, 4.0, 8.0]


def test_auth_error_401_immediate_no_retry():
    sleeps = []
    p, seen = _provider([httpx.Response(401)], sleeps)
    with pytest.raises(ProviderUnavailable):
        p.complete(MSGS, AskDraft)
    assert len(seen) == 1 and sleeps == []


def test_auth_error_403_immediate_no_retry():
    sleeps = []
    p, seen = _provider([httpx.Response(403)], sleeps)
    with pytest.raises(ProviderUnavailable):
        p.complete(MSGS, AskDraft)
    assert len(seen) == 1 and sleeps == []


def test_client_error_and_bad_json_are_not_retried_not_unavailable():
    for response in (httpx.Response(400), _ok("not json"), _ok('{"status": "maybe"}')):
        sleeps = []
        p, seen = _provider([response], sleeps)
        with pytest.raises(ProviderError) as exc_info:
            p.complete(MSGS, AskDraft)
        assert not isinstance(exc_info.value, ProviderUnavailable)
        assert len(seen) == 1 and sleeps == []


def test_make_provider():
    assert make_provider({}) is None
    assert make_provider({"LLM_PROVIDER": "none"}) is None
    with pytest.raises(ValueError):
        make_provider({"LLM_PROVIDER": "groq", "LLM_MODEL": "m"})
    with pytest.raises(ValueError):
        make_provider({"LLM_PROVIDER": "openrouter"})
    p = make_provider({"LLM_PROVIDER": "gemini", "GEMINI_API_KEY": "k", "LLM_MODEL": "g"})
    assert (p.name, p.model) == ("gemini", "g") and p.min_interval == 2.5
    blank = make_provider({"LLM_PROVIDER": "gemini", "GEMINI_API_KEY": "k", "LLM_MODEL": "g",
                           "LLM_MIN_INTERVAL": ""})
    assert blank.min_interval == 2.5  # empty .env value falls back to the default


def test_load_env_file_keeps_real_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("IFLA_T_A", "0")
    monkeypatch.setenv("IFLA_T_B", "")
    monkeypatch.delenv("IFLA_T_B")
    env = tmp_path / ".env"
    env.write_text("IFLA_T_A=1\n# comment\nIFLA_T_B = 'two'\n\n", encoding="utf-8")
    load_env_file(env)
    load_env_file(tmp_path / "missing.env")
    assert os.environ["IFLA_T_A"] == "0" and os.environ["IFLA_T_B"] == "two"
