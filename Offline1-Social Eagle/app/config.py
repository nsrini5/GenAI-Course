"""Central configuration, read from environment variables (.env in Docker)."""
import os
from pathlib import Path


def _load_dotenv(path: str = ".env") -> None:
    """Load KEY=VALUE lines from .env (no extra dependency). Real env vars win."""
    f = Path(path)
    if not f.is_file():
        return
    for line in f.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


DOCS_DIR = Path(os.getenv("DOCS_DIR", "data/docs"))
INDEX_DIR = Path(os.getenv("INDEX_DIR", "data/index"))

# Stage 2 – text splitter
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "700"))          # characters
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "120"))

# Stage 3 – embedding
EMBED_BACKEND = os.getenv("EMBED_BACKEND", "fastembed")    # fastembed | lsa
EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-small-en-v1.5")

# Stage 4 – vector DB (Qdrant). Empty URL = embedded Qdrant on disk (no server needed).
QDRANT_URL = os.getenv("QDRANT_URL", "")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY", "")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "spotify_architecture")

# Stage 5/6 – entity extraction & relationship mapping
KG_EXTRACTOR = os.getenv("KG_EXTRACTOR", "rules")          # rules | llm (rules + LLM triples)
KG_HOPS = int(os.getenv("KG_HOPS", "1"))
KG_MAX_FACTS = int(os.getenv("KG_MAX_FACTS", "12"))

# Graph DB (Neo4j). Empty URI = in-memory networkx graph only (graph.json on disk).
NEO4J_URI = os.getenv("NEO4J_URI", "")                    # e.g. bolt://neo4j:7687
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

# Retrieval / fusion
TOP_K = int(os.getenv("TOP_K", "5"))
CANDIDATES = int(os.getenv("CANDIDATES", "20"))
RRF_K = int(os.getenv("RRF_K", "60"))
BM25_WEIGHT = float(os.getenv("BM25_WEIGHT", "1.0"))
DENSE_WEIGHT = float(os.getenv("DENSE_WEIGHT", "1.0"))
GRAPH_WEIGHT = float(os.getenv("GRAPH_WEIGHT", "1.0"))

# Generation
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "none")           # anthropic | openai | ollama | none
LLM_MODEL = os.getenv("LLM_MODEL", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "800"))

# API
API_KEY = os.getenv("API_KEY", "")
AUTO_INGEST = _bool("AUTO_INGEST", True)
