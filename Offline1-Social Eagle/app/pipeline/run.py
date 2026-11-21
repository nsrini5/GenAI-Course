"""Ingestion pipeline – runs the six stages in order and reports on each.

  1. Document loader        -> loader.load_documents
  2. Text splitter          -> splitter.split_documents
  3. Embedding              -> embeddings.make_embedder / embed_documents
  4. Vector DB (Qdrant)     -> vectordb.VectorStore.upsert
  5. Entity extraction      -> entities.extract_entities
  6. Relationship mapping   -> relations.map_relations  (+ Neo4j sync)
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from app import config
from app.pipeline.embeddings import make_embedder, save_embedder
from app.pipeline.entities import extract_entities
from app.pipeline.loader import load_documents
from app.pipeline.relations import Neo4jGraph, map_relations, neo4j_enabled
from app.pipeline.splitter import split_documents
from app.pipeline.vectordb import VectorStore
from app.retriever import HybridRetriever

log = logging.getLogger("pipeline")


def run_ingest(docs_dir: Path | None = None, index_dir: Path | None = None) -> tuple[HybridRetriever, list[dict]]:
    d = index_dir or config.INDEX_DIR
    d.mkdir(parents=True, exist_ok=True)
    report: list[dict] = []

    def stage(n: int, name: str, t0: float, **info):
        row = {"stage": n, "name": name, "seconds": round(time.perf_counter() - t0, 2), **info}
        report.append(row)
        log.info("Stage %d %-22s %s", n, name, {k: v for k, v in row.items() if k not in ("stage", "name")})

    t = time.perf_counter()
    docs = load_documents(docs_dir)
    if not docs:
        raise ValueError(f"No documents found in {docs_dir or config.DOCS_DIR}")
    stage(1, "document_loader", t, documents=len({x.metadata["source"] for x in docs}), pages=len(docs))

    t = time.perf_counter()
    chunks = split_documents(docs)
    (d / "chunks.json").write_text(json.dumps([c.to_dict() for c in chunks], indent=1))
    stage(2, "text_splitter", t, chunks=len(chunks), sections=len({c.section for c in chunks}))

    t = time.perf_counter()
    emb = make_embedder()
    texts = [c.text for c in chunks]
    emb.fit(texts)
    vectors = emb.embed_documents(texts)
    save_embedder(emb, d)
    stage(3, "embedding", t, backend=emb.name, model=getattr(emb, "model_name", "tfidf+svd"), dim=int(vectors.shape[1]))

    t = time.perf_counter()
    store = VectorStore(d)
    store.recreate(int(vectors.shape[1]))
    store.upsert(chunks, vectors)
    stage(4, "vector_db", t, engine="qdrant", mode="server" if config.QDRANT_URL else "embedded",
          collection=store.collection, points=store.count())

    t = time.perf_counter()
    entities = extract_entities(chunks)
    by_type: dict[str, int] = {}
    for e in entities.entities.values():
        by_type[e.type] = by_type.get(e.type, 0) + 1
    (d / "entities.json").write_text(json.dumps([e.to_dict() for e in entities.entities.values()], indent=1))
    stage(5, "entity_extraction", t, entities=len(entities), by_type=by_type)

    t = time.perf_counter()
    kg = map_relations(chunks, entities)
    kg.save(d)
    (d / "graph.cypher").write_text(kg.to_cypher())
    info = kg.stats()
    if neo4j_enabled():
        info.update(Neo4jGraph().sync(kg))
    stage(6, "relationship_mapping", t, **{k: v for k, v in info.items() if k != "node_types"})

    (d / "ingest_report.json").write_text(json.dumps(report, indent=1))
    return HybridRetriever(chunks, emb, store, kg), report
