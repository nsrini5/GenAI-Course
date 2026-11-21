"""STAGE 3 – Embedding.

Default: BAAI/bge-small-en-v1.5 (384-d) through fastembed (ONNX runtime, CPU, no PyTorch).
Fallback: LSA (TF-IDF + truncated SVD) when the model can't be downloaded,
so the pipeline still runs on an air-gapped VPS or in CI.
"""
from __future__ import annotations

import logging
import pickle
from pathlib import Path

import numpy as np

from app import config

log = logging.getLogger(__name__)


def _normalize(v: np.ndarray) -> np.ndarray:
    return (v / (np.linalg.norm(v, axis=1, keepdims=True) + 1e-12)).astype(np.float32)


class FastEmbedder:
    name = "fastembed"

    def __init__(self, model: str = config.EMBED_MODEL):
        from fastembed import TextEmbedding

        self.model_name = model
        self.model = TextEmbedding(model)

    def fit(self, texts: list[str]) -> None:
        pass  # pretrained

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        return _normalize(np.array(list(self.model.passage_embed(texts))))

    def embed_query(self, text: str) -> np.ndarray:
        return _normalize(np.array(list(self.model.query_embed([text]))))[0]

    @property
    def dim(self) -> int:
        return self.embed_query("dim").shape[0]


class LSAEmbedder:
    name = "lsa"

    def __init__(self, dims: int = 128):
        from sklearn.feature_extraction.text import TfidfVectorizer

        self.vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, stop_words="english")
        self.dims, self.svd = dims, None

    def fit(self, texts: list[str]) -> None:
        from sklearn.decomposition import TruncatedSVD

        x = self.vec.fit_transform(texts)
        n = max(2, min(self.dims, x.shape[1] - 1, x.shape[0] - 1))
        self.svd = TruncatedSVD(n_components=n, random_state=42).fit(x)

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        return _normalize(self.svd.transform(self.vec.transform(texts)))

    def embed_query(self, text: str) -> np.ndarray:
        return self.embed_documents([text])[0]

    @property
    def dim(self) -> int:
        return self.svd.n_components


def make_embedder():
    if config.EMBED_BACKEND == "fastembed":
        try:
            return FastEmbedder(config.EMBED_MODEL)
        except Exception as e:
            log.warning("fastembed unavailable (%s) – falling back to LSA embeddings", e)
    return LSAEmbedder()


def save_embedder(emb, d: Path) -> None:
    if isinstance(emb, LSAEmbedder):
        with open(d / "lsa.pkl", "wb") as f:
            pickle.dump(emb, f)
    (d / "embedder.txt").write_text(f"{emb.name}\n{getattr(emb, 'model_name', '')}")


def load_embedder(d: Path):
    name, model = ((d / "embedder.txt").read_text().splitlines() + [""])[:2]
    if name == "lsa":
        with open(d / "lsa.pkl", "rb") as f:
            return pickle.load(f)
    return FastEmbedder(model)
