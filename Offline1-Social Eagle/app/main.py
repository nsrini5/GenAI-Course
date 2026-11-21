"""FastAPI service exposing the Hybrid RAG + Knowledge Graph pipeline."""
from __future__ import annotations

import logging
import shutil
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app import config
from app.llm import generate
from app.pipeline.relations import Neo4jGraph, neo4j_enabled
from app.pipeline.run import run_ingest
from app.retriever import HybridRetriever

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("hybrid-rag")
STATE: dict = {"retriever": None, "report": []}
STATIC = Path(__file__).parent / "static"


def rebuild() -> list[dict]:
    STATE["retriever"], STATE["report"] = run_ingest()
    return STATE["report"]


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        STATE["retriever"] = HybridRetriever.load()
        if STATE["retriever"].store.count() == 0:
            raise FileNotFoundError("vector collection empty")
        log.info("Loaded existing index (%d chunks)", len(STATE["retriever"].chunks))
        if neo4j_enabled():
            try:
                neo = Neo4jGraph()
                if neo.count() == 0:
                    log.info("Neo4j is empty - syncing knowledge graph")
                    log.info("Neo4j sync: %s", neo.sync(STATE["retriever"].kg, retries=3))
                else:
                    log.info("Neo4j has %d entities", neo.count())
            except Exception as e:
                log.warning("Neo4j check failed (%s) - graph search will use the local graph", e)
    except (FileNotFoundError, ValueError) as e:
        if config.AUTO_INGEST:
            log.info("No usable index (%s) – running ingestion pipeline", e)
            rebuild()
    yield


app = FastAPI(title="Hybrid RAG + Knowledge Graph – Spotify Architecture", version="2.0.0", lifespan=lifespan)


def require_key(x_api_key: str | None = Header(default=None)):
    if config.API_KEY and x_api_key != config.API_KEY:
        raise HTTPException(401, "Invalid or missing X-API-Key header")


def R() -> HybridRetriever:
    if STATE["retriever"] is None:
        raise HTTPException(503, "Index not built yet. POST /ingest first.")
    return STATE["retriever"]


class QueryIn(BaseModel):
    question: str = Field(..., min_length=2, max_length=2000)
    top_k: int = Field(config.TOP_K, ge=1, le=20)
    mode: str = Field("hybrid", pattern="^(hybrid|bm25|dense|graph)$")


@app.get("/")
def ui():
    return FileResponse(STATIC / "index.html")


@app.get("/graph-view")
def graph_view():
    return FileResponse(STATIC / "graph.html")


@app.get("/health")
def health():
    r = STATE["retriever"]
    return {
        "status": "ok",
        "chunks": len(r.chunks) if r else 0,
        "vectors": r.store.count() if r else 0,
        "embedding": r.embedder.name if r else None,
        "graph": r.kg.stats() if r else None,
        "neo4j": (Neo4jGraph().ping() if neo4j_enabled() else "disabled"),
        "llm_provider": config.LLM_PROVIDER,
    }


@app.get("/pipeline", dependencies=[Depends(require_key)])
def pipeline_report():
    return {"stages": STATE["report"]}


@app.post("/ingest", dependencies=[Depends(require_key)])
def ingest():
    return {"stages": rebuild()}


@app.post("/upload", dependencies=[Depends(require_key)])
async def upload(file: UploadFile = File(...)):
    name = Path(file.filename or "").name
    if Path(name).suffix.lower() not in {".pdf", ".txt", ".md"}:
        raise HTTPException(400, "Only .pdf, .txt, .md are supported")
    config.DOCS_DIR.mkdir(parents=True, exist_ok=True)
    with open(config.DOCS_DIR / name, "wb") as out:
        shutil.copyfileobj(file.file, out)
    return {"saved": name, "stages": rebuild()}


@app.post("/search", dependencies=[Depends(require_key)])
def search(q: QueryIn):
    return R().search(q.question, q.top_k, q.mode)


@app.post("/query", dependencies=[Depends(require_key)])
def query(q: QueryIn):
    res = R().search(q.question, q.top_k, q.mode)
    try:
        answer = generate(q.question, res["hits"], res["facts"])
    except Exception as e:
        log.exception("LLM call failed")
        raise HTTPException(502, f"LLM call failed: {e}")
    keep = ("id", "section", "page", "score", "bm25_rank", "dense_rank", "graph_rank")
    return {"answer": answer, "entities": res["entities"], "facts": res["facts"],
            "sources": [{k: h[k] for k in keep} for h in res["hits"]]}


@app.get("/graph", dependencies=[Depends(require_key)])
def graph():
    return {**R().kg.stats(), **R().kg.to_vis()}


@app.get("/graph/entity/{name:path}", dependencies=[Depends(require_key)])
def graph_entity(name: str):
    e = R().kg.entity(name)
    if not e:
        raise HTTPException(404, f"No entity matching '{name}'")
    return e
