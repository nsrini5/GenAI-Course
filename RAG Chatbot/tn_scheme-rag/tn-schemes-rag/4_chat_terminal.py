"""
Terminal version of the chatbot - no browser or Streamlit needed.
Use it to test the RAG pipeline while the web page issue is being fixed.

Run:  python 4_chat_terminal.py
Type 'exit' to quit.  Type 'lang Tamil' (or Hindi, English, auto...) to change answer language.
"""
import os

import chromadb
from chromadb.utils import embedding_functions
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
DB_DIR, COLLECTION = "chroma_db", "tn_schemes"
EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
TOP_K = 8


def system_prompt(lang: str) -> str:
    rule = ("Reply in the same language the user writes in." if lang == "auto"
            else f"Always reply in {lang}, whatever language the question is in.")
    return ("You are an assistant that answers questions about Tamil Nadu Government schemes.\n"
            "Use ONLY the context provided. If the answer is not in the context, say you couldn't "
            "find it in the scheme information available. Do not guess.\n"
            "When relevant, structure answers as: Scheme name, Objective, Eligibility, Benefits, "
            "How to apply, Contact. Keep scheme names, amounts and dates exactly as in the context.\n"
            "For questions asking to list, count or find schemes, use the FULL SCHEME LIST given in the context.\n"
            + rule)


def main():
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("OPENAI_API_KEY missing - add it to the .env file")
    print("Loading search index (first time ~20 s)...")
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBED_MODEL)
    col = chromadb.PersistentClient(path=DB_DIR).get_collection(COLLECTION, embedding_function=ef)
    llm = OpenAI()
    titles = sorted({m["title"] for m in col.get(include=["metadatas"])["metadatas"]} - {"Scheme list"})
    catalogue = f"FULL SCHEME LIST ({len(titles)} schemes):\n" + "\n".join(f"- {t}" for t in titles)
    lang, history = "auto", []
    print(f"Ready. {col.count()} chunks indexed. Ask a question (or 'exit').\n")

    while True:
        q = input("You: ").strip()
        if not q:
            continue
        if q.lower() in ("exit", "quit"):
            break
        if q.lower().startswith("lang "):
            lang = q[5:].strip() or "auto"
            print(f"[Answer language set to: {lang}]\n")
            continue

        search_q = llm.chat.completions.create(
            model=MODEL, temperature=0,
            messages=[{"role": "system", "content": "Translate the user's text to English. If already "
                       "English, return it unchanged. Output only the translation."},
                      {"role": "user", "content": q}]).choices[0].message.content.strip()
        res = col.query(query_texts=[search_q], n_results=TOP_K)
        docs, metas = res["documents"][0], res["metadatas"][0]
        context = "\n\n---\n\n".join(f"[Source {i+1}: {m['title']}]\n{d}" for i, (d, m) in enumerate(zip(docs, metas)))

        messages = [{"role": "system", "content": system_prompt(lang)}] + history[-6:]
        messages.append({"role": "user", "content": f"Context:\n{catalogue}\n\n{context}\n\nQuestion: {q}"})
        ans = llm.chat.completions.create(model=MODEL, messages=messages, temperature=0.1).choices[0].message.content

        print(f"\nBot: {ans}\n")
        print("Sources:")
        for m in {m["url"]: m for m in metas}.values():
            print(f"  - {m['title']}: {m['url']}")
        print()
        history += [{"role": "user", "content": q}, {"role": "assistant", "content": ans}]


if __name__ == "__main__":
    main()
