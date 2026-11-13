"""Multi-PDF RAG app with page-level sources.

Run with: streamlit run rag_app.py
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Iterable

import streamlit as st
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

st.set_page_config(page_title="Multi-PDF RAG", page_icon="📚", layout="wide")
st.title("📚 Multi-PDF RAG with Sources")
st.caption("Ask grounded questions across several PDFs and inspect the exact file/page evidence.")


def load_uploaded_pdfs(files: Iterable) -> list[Document]:
    """Persist uploads briefly so PyPDFLoader can preserve page metadata."""
    pages: list[Document] = []
    for uploaded in files:
        suffix = Path(uploaded.name).suffix or ".pdf"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded.getbuffer())
            path = tmp.name
        try:
            loaded = PyPDFLoader(path).load()
            for doc in loaded:
                # PyPDFLoader uses zero-based `page`; expose human page numbers.
                page_number = int(doc.metadata.get("page", 0)) + 1
                doc.metadata.update({"source": uploaded.name, "page": page_number})
                pages.append(doc)
        finally:
            Path(path).unlink(missing_ok=True)
    return pages


def build_store(files: list) -> tuple[FAISS, int, int]:
    pages = load_uploaded_pdfs(files)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000, chunk_overlap=150, add_start_index=True
    )
    chunks = splitter.split_documents(pages)
    if not chunks:
        raise ValueError("No readable text was found in the uploaded PDFs.")
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    return FAISS.from_documents(chunks, embeddings), len(chunks), len(pages)


def answer_question(store: FAISS, question: str, k: int = 6):
    # Smaller, cost-efficient model suitable for this Streamlit assignment.
    llm = ChatOpenAI(model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"), temperature=0)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You answer questions using only the supplied document excerpts. """
                """If the excerpts conflict, explicitly say they disagree and """
                """summarize each position with its source. If the answer is not """
                """supported, say you cannot find it in the uploaded PDFs. """
                """Do not invent citations.\n\n<context>\n{context}\n</context>""",
            ),
            ("human", "{input}"),
        ]
    )
    # Use the retriever and model directly. This avoids the removed
    # `langchain.chains` namespace in newer LangChain releases.
    docs = store.as_retriever(search_kwargs={"k": k}).invoke(question)
    context = "\n\n".join(
        f"Source: {doc.metadata.get('source', 'unknown')} - page "
        f"{doc.metadata.get('page', '?')}\n{doc.page_content}"
        for doc in docs
    )
    response = llm.invoke(prompt.invoke({"context": context, "input": question}))
    return {"answer": response.content, "context": docs}


with st.sidebar:
    st.header("Settings")
    st.info("Upload two or more PDFs to compare them in one vector store.")
    top_k = st.slider("Retrieved chunks", min_value=3, max_value=10, value=6)
    if os.getenv("LANGCHAIN_TRACING_V2", "false").lower() == "true":
        st.success("LangSmith tracing is enabled")
    else:
        st.caption("LangSmith tracing is off. Set LANGCHAIN_TRACING_V2=true to enable it.")

files = st.file_uploader(
    "Upload PDFs", type=["pdf"], accept_multiple_files=True, help="All files are indexed together."
)

if files:
    names = [f.name for f in files]
    fingerprint = tuple((f.name, f.size) for f in files)
    if st.session_state.get("upload_fingerprint") != fingerprint:
        if not os.getenv("OPENAI_API_KEY"):
            st.error("OPENAI_API_KEY is missing. Add it to .env, then restart Streamlit.")
            st.stop()
        with st.spinner("Loading, chunking, and embedding your PDFs..."):
            try:
                store, chunk_count, page_count = build_store(files)
                st.session_state.update(
                    store=store,
                    chunk_count=chunk_count,
                    page_count=page_count,
                    upload_fingerprint=fingerprint,
                    upload_names=names,
                )
            except Exception as exc:
                st.error(f"Indexing failed: {exc}")
                st.stop()

    st.success(
        f"Indexed {st.session_state['chunk_count']} chunks from "
        f"{len(st.session_state['upload_names'])} PDF(s) across "
        f"{st.session_state['page_count']} pages."
    )
    st.caption("Files: " + ", ".join(st.session_state["upload_names"]))

    with st.form("question_form", clear_on_submit=False):
        question = st.text_input(
            "Ask a question about the uploaded PDFs",
            key="question_input",
            placeholder="Type a new question, then click Ask",
        )
        ask = st.form_submit_button("Ask", type="primary")

    if ask and question.strip():
        with st.spinner("Searching sources and drafting an answer..."):
            try:
                result = answer_question(st.session_state["store"], question, top_k)
                st.subheader("Answer")
                st.write(result["answer"])
                st.subheader("Sources")
                seen = set()
                for doc in result.get("context", []):
                    source = doc.metadata.get("source", "unknown file")
                    page = doc.metadata.get("page", "?")
                    key = (source, page)
                    if key not in seen:
                        st.caption(f"📄 {source} — page {page}")
                        seen.add(key)
            except Exception as exc:
                st.error(f"Question failed: {exc}")
else:
    st.warning("Upload one or more PDFs to begin. The Tata Tea case PDF can be uploaded here.")
