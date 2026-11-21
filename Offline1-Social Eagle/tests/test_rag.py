"""Pipeline tests against the Spotify architecture PDF (offline: LSA embeddings, embedded Qdrant, no Neo4j)."""
import os

os.environ.setdefault("EMBED_BACKEND", "lsa")
os.environ.setdefault("LLM_PROVIDER", "none")
os.environ["QDRANT_URL"] = ""
os.environ["NEO4J_URI"] = ""
os.environ["API_KEY"] = ""          # .env may set one; tests call the API without it

import pytest
from fastapi.testclient import TestClient

from app.pipeline.entities import extract_entities
from app.pipeline.loader import load_documents
from app.pipeline.run import run_ingest
from app.pipeline.splitter import split_documents


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    return run_ingest(index_dir=tmp_path_factory.mktemp("idx"))


# ---- stage 1 & 2
def test_loader_and_splitter():
    docs = load_documents()
    assert len(docs) == 6 and docs[0].metadata["source"].endswith(".pdf")
    chunks = split_documents(docs)
    assert len(chunks) > 20
    assert any("Media Processor" in c.section for c in chunks)
    assert all(not c.body[:1].islower() for c in chunks), "chunks should start on a line boundary"


# ---- stage 3 & 4
def test_report_has_six_stages(built):
    _, report = built
    assert [s["name"] for s in report] == [
        "document_loader", "text_splitter", "embedding", "vector_db", "entity_extraction", "relationship_mapping"]
    assert report[3]["points"] == report[1]["chunks"]


# ---- stage 5
def test_entities():
    idx = extract_entities(split_documents(load_documents()))
    types = {e.type for e in idx.entities.values()}
    assert {"Service", "Technology", "Table", "Event", "Feature", "Data", "Route", "Layer"} <= types
    assert len(idx.of_type("Service")) == 17
    assert "Table:playlist_tracks" in idx.entities and "Event:track_uploaded" in idx.entities


# ---- stage 6
def _has_edge(kg, s, rel, t):
    return any(d["rel"] == rel for d in (kg.g.get_edge_data(s, t) or {}).values())


def test_relations(built):
    kg = built[0].kg
    assert _has_edge(kg, "Service:Media Processor Service", "USES", "Technology:FFmpeg")
    assert _has_edge(kg, "Service:Playback & Session Service", "OWNS", "Table:playback_queue")
    assert _has_edge(kg, "Service:Media Processor Service", "INTERACTS_WITH", "Service:Catalog Service (Music Metadata)")
    assert _has_edge(kg, "Service:Analytics & Events Service", "INTERACTS_WITH", "Service:Recommendation & Personalization Service")
    assert _has_edge(kg, "Technology:Kafka", "CARRIES", "Event:track_uploaded")
    assert _has_edge(kg, "Feature:B. Playback & Player", "IMPLEMENTED_BY", "Service:Playback & Session Service")
    assert _has_edge(kg, "Layer:Frontend", "USES", "Technology:Next.js")
    assert "MERGE" in kg.to_cypher()


# ---- retrieval
@pytest.mark.parametrize("question, expected", [
    ("Which service transcodes uploads with FFmpeg?", "Media Processor"),
    ("Where are playback events like skip and complete stored?", "Data Storage"),
    ("How are subscription plans and invoices handled?", "Subscription & Billing"),
    ("frequency caps for audio ads", "Ads"),
    ("What does the playback_queue table belong to?", "Playback & Session"),
])
def test_hybrid_top3(built, question, expected):
    hits = built[0].search(question, k=3)["hits"]
    assert any(expected in h["section"] for h in hits), [h["section"] for h in hits]


def test_graph_retrieval(built):
    res = built[0].search("Which services does the Media Processor notify?", mode="graph")
    assert "Media Processor Service" in res["entities"]
    objs = {f["object"] for f in res["facts"] if f["relation"] == "INTERACTS_WITH"}
    assert any("Catalog" in o for o in objs) and any("Streaming" in o for o in objs)


def test_api(tmp_path, monkeypatch):
    from app import config, main

    monkeypatch.setattr(config, "INDEX_DIR", tmp_path)
    with TestClient(main.app) as c:
        h = c.get("/health").json()
        assert h["chunks"] > 0 and h["vectors"] == h["chunks"] and h["graph"]["edges"] > 50
        r = c.post("/query", json={"question": "Which database is used for full-text search?"}).json()
        assert r["sources"] and r["facts"]
        assert c.get("/graph/entity/Redis").json()["type"] == "Technology"
        assert len(c.get("/pipeline").json()["stages"]) == 6
