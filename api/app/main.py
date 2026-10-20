"""HTTP API (spec 9). Run from api/:
HF_HUB_OFFLINE=1 HF_HOME=<repo>/.cache/huggingface .venv/Scripts/python -m uvicorn app.main:app --port 8000
Models load at startup (about a minute on CPU); /ask and /navigator take ~45 s each on CPU
because of the reranker (Fase 2 measurement)."""

from __future__ import annotations

import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.config import cors_origins
from app.faraid import FaraidRequest, FaraidResult, hitung_faraid
from app.generation.schemas import AskResponse, NavigatorResponse, Sumber
from app.generation.service import Assistant
from app.generation.sources import to_sumber


class Question(BaseModel):
    pertanyaan: str = Field(min_length=5, max_length=2000)


def _build() -> tuple[Assistant, int, object]:
    from app.config import load_env_file
    from app.generation.providers import make_provider
    from app.retrieval.corpus import REPO_ROOT
    from app.retrieval.indexer import open_retriever
    from app.retrieval.models import BGEM3Embedder, BGEReranker

    load_env_file(REPO_ROOT / ".env")
    retriever = open_retriever(REPO_ROOT / "data", REPO_ROOT / "data" / "qdrant",
                               BGEM3Embedder(), BGEReranker())
    assistant = Assistant(retriever.chunks, make_provider(), retriever.search)
    return assistant, retriever.store.count(), retriever.store.close


def create_app(assistant: Assistant | None = None, points: int | None = None) -> FastAPI:
    state = {"assistant": assistant, "points": points}
    # ponytail: one request at a time (Qdrant local mode, CPU reranker); add a worker queue
    # if concurrent users ever matter.
    lock = threading.Lock()

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        close = None
        if state["assistant"] is None:
            state["assistant"], state["points"], close = _build()
        yield
        if close is not None:
            close()

    api = FastAPI(title="Islamic Family Law Assistant", lifespan=lifespan)
    api.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins(),
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @api.get("/health")
    def health() -> dict:
        a = state["assistant"]
        return {"status": "ok", "chunks": len(a.chunks), "index_points": state["points"],
                "mode": "llm" if a.provider else "retrieval_only",
                "llm": f"{a.provider.name}/{a.provider.model}" if a.provider else None}

    @api.post("/navigator", response_model=NavigatorResponse)
    def navigator(q: Question) -> NavigatorResponse:
        with lock:
            return state["assistant"].navigator(q.pertanyaan).response

    @api.post("/ask", response_model=AskResponse)
    def ask(q: Question) -> AskResponse:
        with lock:
            return state["assistant"].ask(q.pertanyaan).response

    @api.post("/faraid", response_model=FaraidResult)
    def faraid(req: FaraidRequest) -> FaraidResult:
        result = hitung_faraid(req)  # numbers come from the engine only
        a = state["assistant"]
        if a is not None:
            result.penjelasan = a.jelaskan_faraid(result)
        return result

    @api.get("/documents/{chunk_id}", response_model=Sumber)
    def document(chunk_id: str) -> Sumber:
        chunk = state["assistant"].chunks.get(chunk_id)
        if chunk is None or chunk.visibility != "public":
            raise HTTPException(status_code=404, detail="chunk not found")
        return to_sumber(chunk)

    return api


app = create_app()
