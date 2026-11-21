.PHONY: venv install test ingest ask run neo4j-local docker-up docker-logs docker-down

venv:
	python3 -m venv .venv

install:
	.venv/bin/pip install -r requirements-dev.txt

test:
	EMBED_BACKEND=lsa LLM_PROVIDER=none QDRANT_URL= NEO4J_URI= .venv/bin/pytest -q

ingest:
	.venv/bin/python -m scripts.ingest

ask:
	.venv/bin/python -m scripts.ingest --ask "$(Q)"

run:
	.venv/bin/uvicorn app.main:app --reload --port 8000

# Qdrant + Neo4j only (for local dev on the Mac with Docker Desktop)
neo4j-local:
	docker compose up -d qdrant neo4j

docker-up:
	docker compose up -d --build

docker-logs:
	docker compose logs -f rag

docker-down:
	docker compose down
