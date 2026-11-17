"""
Step 2: Chunk the scraped / manually saved content, embed it, store in a local Chroma vector DB.
Sources read:
  - data/raw/*.jsonl              (from 1_scrape.py and 6_crawl_sites.py)
  - data/manual/*.html|*.htm|*.pdf|*.txt   (pages you saved by hand)

Run:  python 2_build_index.py
"""
import json
from pathlib import Path

import chromadb
from bs4 import BeautifulSoup
from chromadb.utils import embedding_functions
from pypdf import PdfReader

RAW_DIR = Path("data/raw")  # schemes.jsonl (tn.gov.in) + sites.jsonl (department websites)
MANUAL = Path("data/manual")
DB_DIR = "chroma_db"
COLLECTION = "tn_schemes"
# Multilingual model: handles English + Tamil text, runs locally, free
EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CHUNK_SIZE, CHUNK_OVERLAP = 1000, 150


def load_documents() -> list[dict]:
    docs = []
    for raw in sorted(RAW_DIR.glob("*.jsonl")):
        for line in raw.read_text(encoding="utf-8").splitlines():
            if line.strip():
                docs.append(json.loads(line))
    for p in sorted(MANUAL.glob("**/*")):
        suf = p.suffix.lower()
        if suf in (".html", ".htm"):
            soup = BeautifulSoup(p.read_text(encoding="utf-8", errors="ignore"), "lxml")
            for t in soup(["script", "style", "nav", "header", "footer", "noscript"]):
                t.decompose()
            title = soup.title.get_text(strip=True) if soup.title else p.stem
            text = "\n".join(l.strip() for l in soup.get_text("\n").splitlines() if l.strip())
        elif suf == ".pdf":
            title = p.stem
            text = "\n".join((pg.extract_text() or "") for pg in PdfReader(str(p)).pages)
        elif suf == ".txt":
            title, text = p.stem, p.read_text(encoding="utf-8", errors="ignore")
        else:
            continue
        docs.append({"url": str(p), "title": title, "text": text})
    return [d for d in docs if d["text"].strip()]


def chunk(text: str) -> list[str]:
    """Paragraph-aware splitter with overlap."""
    paras, chunks, cur = text.split("\n"), [], ""
    for para in paras:
        if len(cur) + len(para) + 1 <= CHUNK_SIZE:
            cur += para + "\n"
        else:
            if cur.strip():
                chunks.append(cur.strip())
            cur = (cur[-CHUNK_OVERLAP:] if CHUNK_OVERLAP else "") + para + "\n"
            while len(cur) > CHUNK_SIZE:  # very long single paragraph
                chunks.append(cur[:CHUNK_SIZE])
                cur = cur[CHUNK_SIZE - CHUNK_OVERLAP:]
    if cur.strip():
        chunks.append(cur.strip())
    return chunks


def main():
    docs = load_documents()
    if not docs:
        raise SystemExit("No documents found. Run 1_scrape.py or put saved pages in data/manual/")

    client = chromadb.PersistentClient(path=DB_DIR)
    try:
        client.delete_collection(COLLECTION)  # rebuild fresh each run
    except Exception:
        pass
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)
    col = client.create_collection(COLLECTION, embedding_function=ef, metadata={"hnsw:space": "cosine"})

    ids, texts, metas = [], [], []
    for d_i, d in enumerate(docs):
        for c_i, c in enumerate(chunk(d["text"])):
            ids.append(f"{d_i}-{c_i}")
            texts.append(f"Scheme: {d['title']}\n{c}")
            metas.append({"title": d["title"], "url": d["url"], "department": d.get("department", "")})

    B = 64
    for i in range(0, len(ids), B):
        col.add(ids=ids[i:i + B], documents=texts[i:i + B], metadatas=metas[i:i + B])
        print(f"Indexed {min(i + B, len(ids))}/{len(ids)} chunks")
    print(f"\nDone: {len(docs)} documents, {len(ids)} chunks -> ./{DB_DIR}")


if __name__ == "__main__":
    main()
