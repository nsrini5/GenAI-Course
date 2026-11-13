# Tata Tea Multi-PDF RAG

This is the Week 2 Day 4 assignment implementation: a single-file Streamlit app that accepts multiple PDFs, chunks and embeds all pages into one FAISS vector database, answers with OpenAI, and displays filename/page sources. It also supports LangSmith tracing through environment variables.

## macOS setup

```bash
cd /path/to/this/folder
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` and add `OPENAI_API_KEY`. Add `LANGCHAIN_API_KEY` and set `LANGCHAIN_TRACING_V2=true` if you want traces in LangSmith.

## Run in VS Code

Open this folder in VS Code, select the `.venv` Python interpreter, open the integrated terminal, and run:

```bash
streamlit run rag_app.py
```

Upload `Tata Tea Limited (A).pdf` and any other PDFs together. The app reports the number of indexed chunks and answers from the shared store. Sources are deduplicated by filename and human-readable page number.

## RAG design

- Ingestion: `PyPDFLoader` loads every uploaded page and preserves source metadata.
- Chunking: `RecursiveCharacterTextSplitter`, 1,000-character chunks with 150-character overlap.
- Embeddings/vector store: OpenAI `text-embedding-3-small` in one FAISS index.
- Retrieval/generation: similarity retrieval of the top-k chunks followed by a grounded `gpt-4o-mini` answer chain.
- The chat model is configurable with `OPENAI_CHAT_MODEL`; the default is the smaller, cost-efficient `gpt-4o-mini`.
- Observability: LangSmith tracing is enabled by environment variables, with project name `tata-tea-multipdf-rag`.
- Reliability behavior: the prompt instructs the model to say when evidence is missing and to surface disagreements between retrieved documents.
