FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FASTEMBED_CACHE_PATH=/models

WORKDIR /srv

COPY requirements.txt .
RUN pip install -r requirements.txt

# Bake the embedding model into the image so containers start offline.
# If the build machine can't reach Hugging Face this step is skipped and
# the app falls back to LSA embeddings at runtime.
ARG EMBED_MODEL=BAAI/bge-small-en-v1.5
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('${EMBED_MODEL}')" \
    || echo 'WARN: embedding model not pre-downloaded'

COPY app ./app
COPY scripts ./scripts
COPY data/docs ./seed-docs

RUN useradd -m -u 1000 rag && mkdir -p /data/docs /data/index && chown -R rag /data /models /srv
USER rag

ENV DOCS_DIR=/data/docs INDEX_DIR=/data/index

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Seed the bundled PDF into the volume on first run, then serve.
CMD sh -c "cp -n /srv/seed-docs/* /data/docs/ 2>/dev/null; \
           exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1"
