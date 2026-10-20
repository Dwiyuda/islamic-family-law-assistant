from __future__ import annotations

import uuid
from pathlib import Path
from typing import Literal

from qdrant_client import QdrantClient, models

from app.ingest.models import Chunk

from .models import Encoded

VectorName = Literal["dense", "sparse"]


def point_id(chunk_id: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id))


def _sparse(weights: dict[int, float]) -> models.SparseVector:
    return models.SparseVector(indices=list(weights), values=list(weights.values()))


class QdrantStore:
    def __init__(self, client: QdrantClient, collection: str = "chunks"):
        self.client, self.collection = client, collection

    @classmethod
    def local(cls, path: Path) -> QdrantStore:
        path.mkdir(parents=True, exist_ok=True)
        return cls(QdrantClient(path=str(path)))

    @classmethod
    def memory(cls) -> QdrantStore:
        return cls(QdrantClient(":memory:"))

    def recreate(self, dim: int) -> None:
        if self.client.collection_exists(self.collection):
            self.client.delete_collection(self.collection)
        self.client.create_collection(
            self.collection,
            vectors_config={"dense": models.VectorParams(size=dim,
                                                         distance=models.Distance.COSINE)},
            sparse_vectors_config={"sparse": models.SparseVectorParams()},
        )

    def upsert(self, chunks: list[Chunk], encoded: list[Encoded]) -> None:
        points = [
            models.PointStruct(
                id=point_id(c.chunk_id),
                vector={"dense": e.dense, "sparse": _sparse(e.sparse)},
                payload={"chunk_id": c.chunk_id, "domain": c.domain,
                         "source_type": c.source_type},
            )
            for c, e in zip(chunks, encoded, strict=True)
        ]
        self.client.upsert(self.collection, points=points)

    def delete(self, chunk_ids: list[str]) -> None:
        if chunk_ids:
            self.client.delete(self.collection, points_selector=models.PointIdsList(
                points=[point_id(cid) for cid in chunk_ids]))

    def has_all(self, chunk_ids: list[str]) -> bool:
        found = 0
        for start in range(0, len(chunk_ids), 256):
            batch = [point_id(cid) for cid in chunk_ids[start:start + 256]]
            found += len(self.client.retrieve(self.collection, ids=batch,
                                              with_payload=False, with_vectors=False))
        return found == len(chunk_ids)

    def count(self) -> int:
        if not self.client.collection_exists(self.collection):
            return 0
        return self.client.count(self.collection).count

    def search(self, using: VectorName, query: Encoded, top_k: int,
               domains: set[str] | None = None) -> list[tuple[str, float]]:
        vector = query.dense if using == "dense" else _sparse(query.sparse)
        flt = None
        if domains:
            flt = models.Filter(must=[models.FieldCondition(
                key="domain", match=models.MatchAny(any=sorted(domains)))])
        result = self.client.query_points(self.collection, query=vector, using=using,
                                          limit=top_k, query_filter=flt, with_payload=True)
        return [(p.payload["chunk_id"], float(p.score)) for p in result.points]

    def close(self) -> None:
        self.client.close()
