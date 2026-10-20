"""LLM access (spec 6.1): one OpenAI-compatible chat-completions client for Groq and Gemini."""

from __future__ import annotations

import os
import time
from collections.abc import Callable, Mapping
from typing import Protocol

import httpx
from pydantic import BaseModel

BASE_URLS = {"groq": "https://api.groq.com/openai/v1",
             "gemini": "https://generativelanguage.googleapis.com/v1beta/openai"}
KEY_VARS = {"groq": "GROQ_API_KEY", "gemini": "GEMINI_API_KEY"}


class ProviderError(RuntimeError):
    """No usable answer from the LLM; callers fall back to retrieval-only."""


class ProviderUnavailable(ProviderError):
    """Provider unreachable, rate-limited or rejecting our credentials; retry later."""


class LLMProvider(Protocol):
    name: str
    model: str

    def complete(self, messages: list[dict], schema: type[BaseModel]) -> dict: ...


def _backoff(response: httpx.Response | None, attempt: int) -> float:
    header = response.headers.get("retry-after") if response is not None else None
    if header and header.replace(".", "", 1).isdigit():
        return min(60.0, float(header))
    return min(60.0, 2.0 * 2 ** attempt)


class OpenAICompatProvider:
    def __init__(self, name: str, model: str, api_key: str, base_url: str,
                 max_retries: int = 3, min_interval: float = 0.0,
                 client: httpx.Client | None = None,
                 sleep: Callable[[float], None] = time.sleep):
        self.name, self.model, self.max_retries = name, model, max_retries
        self.min_interval, self.sleep = min_interval, sleep
        self._key = api_key
        self._client = client or httpx.Client(base_url=base_url, timeout=90)
        self._last = 0.0

    def _throttle(self) -> None:
        wait = self._last + self.min_interval - time.monotonic()
        if wait > 0:
            self.sleep(wait)
        self._last = time.monotonic()

    def complete(self, messages: list[dict], schema: type[BaseModel]) -> dict:
        body = {"model": self.model, "messages": messages, "temperature": 0,
                "response_format": {"type": "json_object"}}
        for attempt in range(self.max_retries + 1):
            self._throttle()
            response, error = None, None
            try:
                response = self._client.post("/chat/completions", json=body,
                                             headers={"Authorization": f"Bearer {self._key}"})
            except httpx.HTTPError as exc:
                error = exc
            if response is not None and response.status_code == 200:
                try:
                    content = response.json()["choices"][0]["message"]["content"]
                    return schema.model_validate_json(content).model_dump()
                except (KeyError, IndexError, TypeError, ValueError) as exc:
                    raise ProviderError(f"{self.name}: unusable JSON ({exc})") from exc
            if response is not None and response.status_code in (401, 403):
                raise ProviderUnavailable(f"{self.name}: {response.status_code}")
            retryable = (response is None or response.status_code == 429
                         or response.status_code >= 500)
            if not retryable or attempt == self.max_retries:
                if retryable and attempt == self.max_retries:
                    reason = response.status_code if response is not None else error
                    raise ProviderUnavailable(f"{self.name}: request failed ({reason})")
                reason = response.status_code if response is not None else error
                raise ProviderError(f"{self.name}: request failed ({reason})")
            self.sleep(_backoff(response, attempt))
        raise AssertionError("unreachable")


def make_provider(env: Mapping[str, str] | None = None) -> LLMProvider | None:
    env = os.environ if env is None else env
    name = env.get("LLM_PROVIDER", "none") or "none"
    if name == "none":
        return None
    if name not in BASE_URLS:
        raise ValueError(f"LLM_PROVIDER must be one of groq, gemini, none; got {name!r}")
    key, model = env.get(KEY_VARS[name]), env.get("LLM_MODEL")
    if not key or not model:
        raise ValueError(f"LLM_PROVIDER={name} needs {KEY_VARS[name]} and LLM_MODEL")
    return OpenAICompatProvider(name, model, key, BASE_URLS[name],
                                min_interval=float(env.get("LLM_MIN_INTERVAL") or "2.5"))
