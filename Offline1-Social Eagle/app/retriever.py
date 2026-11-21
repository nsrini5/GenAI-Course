"""Hybrid retriever = BM25 (sparse) + Qdrant (dense) + knowledge graph, fused by weighted RRF.

  BM25   -> exact terms: "ClickHouse", "playlist_tracks", "HLS"
  Dense  -> paraphrases: "how are songs converted to different qualities?" -> Media Processor
  Graph  -> structure:   "what does the Media Processor talk to?" -> Catalog + Streaming via INTERACTS_WITH
RRF only uses ranks, so the three score scales never need calibrating.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

from app import config
from app.pipeline.embeddings import load_embedder
from app.pipeline.relations import KnowledgeGraph
from app.pipeline.splitter import Chunk
from app.pipeline.vectordb import VectorStore

TOKEN_RE = re.compile(r"[a-z0-9_]+")
STOP = set("a an and are as at be by for from how i in is it of on or the to what which with does do".split())


def tokenize(text: str) -> list[str]:
    return [t for t in TOKEN_RE.findall(text.lower()) if t not in STOP]


class HybridRetriever:
    def __init__(self, chunks: list[Chunk], embedder, store: VectorStore, kg: KnowledgeGraph):
        self.chunks = chunks
        self.by_id = {c.id: c for c in chunks}
        self.embedder, self.store, self.kg = embedder, store, kg
        self.bm25 = BM25Okapi([tokenize(c.text) for c in chunks])

    @classmethod
    def load(cls, index_dir: Path | None = None) -> "HybridRetriever":
        d = index_dir or config.INDEX_DIR
        chunks = [Chunk(**c) for c in json.loads((d / "chunks.json").read_text())]
        return cls(chunks, load_embedder(d), VectorStore(d), KnowledgeGraph.load(d))

    def _bm25(self, q: str, n: int) -> list[str]:
        s = self.bm25.get_scores(tokenize(q))
        return [self.chunks[i].id for i in np.argsort(-s)[:n] if s[i] > 0]

    def _dense(self, q: str, n: int) -> list[str]:
        return [cid for cid, _ in self.store.search(self.embedder.embed_query(q), n)]

    def search(self, query: str, k: int | None = None, mode: str = "hybrid") -> dict:
        k = k or config.TOP_K
        n = max(config.CANDIDATES, k)
        lists: dict[str, list[str]] = {}
        seeds, facts = [], []
        if mode in ("hybrid", "bm25"):
            lists["bm25"] = self._bm25(query, n)
        if mode in ("hybrid", "dense"):
            lists["dense"] = self._dense(query, n)
        if mode in ("hybrid", "graph"):
            ranked, seeds, facts = self.kg.search(query, n)
            lists["graph"] = [cid for cid, _ in ranked if cid in self.by_id]

        weights = {"bm25": config.BM25_WEIGHT, "dense": config.DENSE_WEIGHT, "graph": config.GRAPH_WEIGHT}
        fused: dict[str, dict] = {}
        for name, ids in lists.items():
            for rank, cid in enumerate(ids, 1):
                e = fused.setdefault(cid, {"score": 0.0, "bm25_rank": None, "dense_rank": None, "graph_rank": None})
                e["score"] += weights[name] / (config.RRF_K + rank)
                e[f"{name}_rank"] = rank

        best = sorted(fused.items(), key=lambda kv: -kv[1]["score"])[:k]
        hits = [{**self.by_id[cid].to_dict(), **info, "score": round(info["score"], 5)} for cid, info in best]
        return {"hits": hits, "entities": seeds, "facts": facts}
