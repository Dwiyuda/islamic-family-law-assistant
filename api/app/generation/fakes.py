"""Deterministic LLM stand-in: unit tests and CI never call a real provider."""

from __future__ import annotations

from pydantic import BaseModel, ValidationError

from .providers import ProviderError


class FakeProvider:
    name = model = "fake"

    def __init__(self, reply: dict | Exception):
        self.reply, self.calls = reply, []

    def complete(self, messages: list[dict], schema: type[BaseModel]) -> dict:
        self.calls.append(messages)
        if isinstance(self.reply, Exception):
            raise self.reply
        try:
            return schema.model_validate(self.reply).model_dump()
        except ValidationError as exc:  # mirror the real provider: bad JSON -> ProviderError
            raise ProviderError(str(exc)) from exc
