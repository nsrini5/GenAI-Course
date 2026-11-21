# Offline1 – Social Eagle · Hybrid RAG + Knowledge Graph

Spotify-like Web App Architecture assistant.

Question-answering over `data/docs/spotify_web_app_architecture.pdf` using **three retrievers** – BM25 (keywords), Qdrant (vectors) and a Neo4j knowledge graph – merged with Reciprocal Rank Fusion, then answered by an LLM with graph facts + cited passages.

Flow: **Mac (VS Code) → GitHub → VPS (git clone/pull) → Docker (app + Qdrant + Neo4j)**

---

## The pipeline (one module per stage, `app/pipeline/`)

```
 PDF ─► 1 Document loader ─► 2 Text splitter ─► 3 Embedding ─► 4 Vector DB (Qdrant)
                                     │
                                     └────────► 5 Entity extraction ─► 6 Relationship mapping ─► Neo4j
 Question ─► BM25  +  Qdrant similarity  +  Graph (entity link → n-hop → facts) ─► RRF fusion ─► LLM answer
```

| # | Stage | File | What happens |
|---|---|---|---|
| 1 | **Document loader** | `loader.py` | Reads PDF/TXT/MD page by page with metadata (source, page, title) |
| 2 | **Text splitter** | `splitter.py` | Splits on the PDF's headings (17 services, storage layout, A–M features), windows long sections (700 chars / 120 overlap) on line boundaries, prefixes each chunk with its section breadcrumb |
| 3 | **Embedding** | `embeddings.py` | `BAAI/bge-small-en-v1.5` (384-d) via fastembed/ONNX on CPU; LSA fallback if the model can't download |
| 4 | **Vector DB** | `vectordb.py` | Qdrant – server in Docker (`http://qdrant:6333`), embedded on-disk mode on your Mac |
| 5 | **Entity extraction** | `entities.py` | 8 entity types: Service, Technology, Table, Event, Data, Feature, Layer, Route (167 entities from this PDF) |
| 6 | **Relationship mapping** | `relations.py` | USES, OWNS, INTERACTS_WITH, STORES, CARRIES, IMPLEMENTED_BY, HAS_ROUTE (167 relations), each with evidence sentence + chunk id; synced to **Neo4j** |
| – | Orchestrator | `run.py` | Runs 1→6 and writes `ingest_report.json` with per-stage stats |
| – | Retriever | `app/retriever.py` | BM25 + Qdrant + graph → weighted RRF |

Example: *"Which services does the Media Processor notify and what tables does Playback own?"* → the graph links **Media Processor Service** and **Playback & Session Service**, returns `Media Processor -[INTERACTS_WITH]-> Catalog`, `Playback & Session -[OWNS]-> playback_queue`, and those facts go into the LLM prompt alongside the passages.

Set `KG_EXTRACTOR=llm` to have the LLM add extra triples on top of the rules (costs tokens per chunk).

---

## Step 1 – Open in VS Code on your Mac

```bash
cd ~/"GenAI Course/Offline1-Social Eagle"
code .        # "code" not found? VS Code > Cmd+Shift+P > "Shell Command: Install 'code' command in PATH"
```
Install the recommended extensions when VS Code prompts (Python, Docker).

## Step 2 – Run and test locally (Mac)

> **Use Python 3.13.** On Python 3.14, `fastembed` (embedding model) can't install yet because `onnxruntime` has no 3.14 build; the app then falls back to LSA embeddings. Install 3.13 with `brew install python@3.13` and create the venv with `python3.13 -m venv .venv`.

```bash
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env               # QDRANT_URL and NEO4J_URI empty = no servers needed
pytest -q                          # expect 11 passed
python -m scripts.ingest --ask "Which services does the Media Processor notify?"
uvicorn app.main:app --reload --port 8000
```
- http://localhost:8000 – ask questions (modes: hybrid / bm25 / dense / graph)
- http://localhost:8000/graph-view – interactive knowledge graph
- http://localhost:8000/docs – API docs

**Optional – real Neo4j + Qdrant on the Mac** (needs Docker Desktop: `brew install --cask docker`):
```bash
docker compose up -d qdrant neo4j
# in .env:  QDRANT_URL=http://localhost:6333   NEO4J_URI=bolt://localhost:7687
curl -X POST -H "X-API-Key: <API_KEY>" localhost:8000/ingest
```
Neo4j Browser: http://localhost:7474 (user `neo4j`, password from `.env`). Try:
```cypher
MATCH (s:Service)-[r]->(x) RETURN s, r, x LIMIT 150
```

For LLM answers set e.g. `LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY=...` in `.env`.

## Step 3 – Push to GitHub (via your existing GenAI Course repo)

This project lives at `GenAI Course/Offline1-Social Eagle/`, inside the **GenAI Course** git repo – no separate repo needed.

VS Code → open the `GenAI Course` folder → terminal:
```bash
cd ~/"GenAI Course"
git add "Offline1-Social Eagle"
git commit -m "Offline1-Social Eagle: hybrid RAG + knowledge graph (Qdrant + Neo4j)"
git push
```
(or use the Source Control panel: stage `Offline1-Social Eagle`, commit, Sync.)

`.env` is git-ignored – keys and passwords stay on the Mac.

**CI (optional):** GitHub only runs workflows from the repo root. To enable tests on every push, move the workflow up one level:
```bash
mkdir -p ~/"GenAI Course/.github/workflows"
mv ~/"GenAI Course/Offline1-Social Eagle/.github/workflows/ci.yml" ~/"GenAI Course/.github/workflows/social-eagle-ci.yml"
```
It already runs inside `Offline1-Social Eagle/` and only triggers when files in that folder change.

## Step 4 – Fetch on the VPS

Minimum: 2 vCPU / 4 GB RAM (Neo4j ~1 GB, Qdrant ~200 MB, app ~500 MB). Ubuntu 22.04/24.04.

```bash
ssh root@<vps-ip>
# Private repo: create a deploy key once
ssh-keygen -t ed25519 -C vps -f ~/.ssh/id_ed25519 -N ""
cat ~/.ssh/id_ed25519.pub          # paste into GitHub repo > Settings > Deploy keys

git clone git@github.com:<your-username>/<genai-course-repo>.git genai-course
cd "genai-course/Offline1-Social Eagle"
```
Optional – fetch only this folder (sparse checkout):
```bash
git clone --filter=blob:none --sparse git@github.com:<your-username>/<genai-course-repo>.git genai-course
cd genai-course && git sparse-checkout set "Offline1-Social Eagle" && cd "Offline1-Social Eagle"
```

## Step 5 – Run in Docker on the VPS

```bash
bash deploy/deploy.sh   # run 1: installs Docker -> log out & back in
bash deploy/deploy.sh   # run 2: creates .env with random API_KEY + NEO4J_PASSWORD
nano .env               # add LLM_PROVIDER + key
bash deploy/deploy.sh   # run 3: builds and starts rag + qdrant + neo4j, then health-checks
```
Compose automatically points the app at `http://qdrant:6333` and `bolt://neo4j:7687`.

Check everything:
```bash
docker compose ps                         # rag, qdrant, neo4j all "Up"
docker compose logs rag | grep Stage      # the 6 pipeline stages
curl localhost:8000/health                # vectors=38, graph edges, neo4j=true
curl -X POST localhost:8000/query -H "Content-Type: application/json" -H "X-API-Key: <API_KEY>" \
  -d '{"question":"Which service owns playlist_tracks and which database stores it?"}'
```
Open the app: `sudo ufw allow 8000` then `http://<vps-ip>:8000`, or use Nginx + HTTPS with `deploy/nginx-hybrid-rag.conf`.

Neo4j and Qdrant dashboards are bound to localhost on the VPS (not public). View them from your Mac through an SSH tunnel:
```bash
ssh -L 7474:localhost:7474 -L 7687:localhost:7687 -L 6333:localhost:6333 root@<vps-ip>
# then open http://localhost:7474 (Neo4j) and http://localhost:6333/dashboard (Qdrant)
```

**Free local LLM:** `LLM_PROVIDER=ollama`, then `docker compose --profile ollama up -d && docker exec -it ollama ollama pull llama3.2:3b` (needs ~4 GB extra RAM).

## Step 6 – Update cycle

Mac: edit → in `GenAI Course`: `git add "Offline1-Social Eagle" && git commit -m "..." && git push`
VPS: `cd ~/genai-course/"Offline1-Social Eagle" && bash deploy/deploy.sh` (it runs `git pull` on the GenAI Course repo, then rebuilds)

Re-run the pipeline (e.g. after changing chunk size or adding docs): `curl -X POST -H "X-API-Key: <key>" localhost:8000/ingest` – it returns the 6-stage report.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | chunk/vector counts, graph stats, Neo4j status |
| POST | `/ingest` | run stages 1–6 |
| GET | `/pipeline` | last ingest report |
| POST | `/upload` | add a PDF/TXT/MD and re-ingest |
| POST | `/search` | retrieval only (`mode`: hybrid, bm25, dense, graph) |
| POST | `/query` | answer + linked entities + graph facts + sources |
| GET | `/graph` | all nodes/edges |
| GET | `/graph/entity/{name}` | one entity with in/out relations |

## Tuning (`.env`)
`CHUNK_SIZE`, `CHUNK_OVERLAP` · `TOP_K`, `CANDIDATES`, `RRF_K` · `BM25_WEIGHT` / `DENSE_WEIGHT` / `GRAPH_WEIGHT` · `KG_HOPS` (1–2) · `KG_MAX_FACTS` · `KG_EXTRACTOR`

## Project layout
```
app/pipeline/  loader.py  splitter.py  embeddings.py  vectordb.py  entities.py  relations.py  run.py
app/           config.py  retriever.py  llm.py  main.py  static/{index,graph}.html
scripts/       ingest.py  export_neo4j.py
tests/         test_rag.py
data/docs/     spotify_web_app_architecture.pdf
deploy/        deploy.sh  nginx-hybrid-rag.conf
Dockerfile  docker-compose.yml  .env.example  Makefile  .github/workflows/ci.yml
```
