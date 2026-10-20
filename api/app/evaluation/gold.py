from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.retrieval.corpus import REPO_ROOT

GOLD_PATH = REPO_ROOT / "eval" / "gold.jsonl"


class GoldItem(BaseModel):
    qid: str = Field(pattern=r"^(cerai|waris|peradilan|luar)-\d{3}$")
    question: str = Field(min_length=10)
    topic: Literal["perceraian", "kewarisan", "peradilan", "luar_domain"]
    relevant_chunk_ids: list[str]
    notes: str | None = None

    @property
    def in_domain(self) -> bool:
        return self.topic != "luar_domain"

    @model_validator(mode="after")
    def _relevance_matches_topic(self) -> GoldItem:
        n = len(self.relevant_chunk_ids)
        if self.in_domain and not 1 <= n <= 5:
            raise ValueError("in-domain questions need 1-5 relevant chunk ids")
        if not self.in_domain and n:
            raise ValueError("out-of-domain questions have no relevant chunks")
        return self


def load_gold(path: Path = GOLD_PATH) -> list[GoldItem]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [GoldItem.model_validate(json.loads(line)) for line in lines if line.strip()]
