"""STAGE 4 – Vector database (Qdrant).

- QDRANT_URL set (Docker / VPS)  -> Qdrant server, e.g. http://qdrant:6333
- QDRANT_URL empty (Mac / tests) -> embedded Qdrant stored under INDEX_DIR/qdrant
Each point = one chunk: vector + payload (id, section, page, source, text).
"""
from __future__ import annotations

import atexit
from pathlib import Path

import numpy as np
from qdrant_client import QdrantClient, models

from app import config
from app.pipeline.splitter import Chunk

_CLIENTS: dict[str, QdrantClient] = {}   # embedded mode allows one client per path


@atexit.register
def _close_all() -> None:
    for c in _CLIENTS.values():
        try:
            c.close()
        except Exception:
            pass


def get_client(index_dir: Path | None = None) -> QdrantClient:
    if config.QDRANT_URL:
        key = config.QDRANT_URL
        if key not in _CLIENTS:
            _CLIENTS[key] = QdrantClient(url=config.QDRANT_URL, api_key=config.QDRANT_API_KEY or None)
    else:
        path = (index_dir or config.INDEX_DIR) / "qdrant"
        path.mkdir(parents=True, exist_ok=True)
        key = str(path.resolve())
        if key not in _CLIENTS:
            _CLIENTS[key] = QdrantClient(path=key)
    return _CLIENTS[key]


class VectorStore:
    def __init__(self, index_dir: Path | None = None, collection: str | None = None):
        self.client = get_client(index_dir)
        self.collection = collection or config.QDRANT_COLLECTION

    def recreate(self, dim: int) -> None:
        if self.client.collection_exists(self.collection):
            self.client.delete_collection(self.collection)
        self.client.create_collection(
            self.collection,
            vectors_config=models.VectorParams(size=dim, distance=models.Distance.COSINE),
        )

    def upsert(self, chunks: list[Chunk], vectors: np.ndarray, batch: int = 128) -> None:
        for i in range(0, len(chunks), batch):
            self.client.upsert(
                self.collection,
                points=[
                    models.PointStruct(id=i + j, vector=vectors[i + j].tolist(), payload=c.to_dict())
                    for j, c in enumerate(chunks[i : i + batch])
                ],
            )

    def search(self, query_vector: np.ndarray, limit: int) -> list[tuple[str, float]]:
        res = self.client.query_points(self.collection, query=query_vector.tolist(), limit=limit, with_payload=["id"])
        return [(p.payload["id"], float(p.score)) for p in res.points]

    def count(self) -> int:
        return self.client.count(self.collection).count if self.client.collection_exists(self.collection) else 0
