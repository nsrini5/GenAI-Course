"""STAGE 1 – Document loader.

Reads PDF / TXT / MD files into page-level Documents with metadata.
Add new formats by adding a function to LOADERS.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader

from app import config


@dataclass
class Document:
    text: str
    metadata: dict = field(default_factory=dict)   # source, page, title


def _load_pdf(path: Path) -> list[Document]:
    reader = PdfReader(str(path))
    title = (reader.metadata.title if reader.metadata else None) or path.stem
    return [
        Document(p.extract_text() or "", {"source": path.name, "page": i + 1, "title": title})
        for i, p in enumerate(reader.pages)
    ]


def _load_text(path: Path) -> list[Document]:
    return [Document(path.read_text(encoding="utf-8", errors="ignore"), {"source": path.name, "page": 1, "title": path.stem})]


LOADERS = {".pdf": _load_pdf, ".txt": _load_text, ".md": _load_text}


def load_documents(docs_dir: Path | None = None) -> list[Document]:
    docs_dir = docs_dir or config.DOCS_DIR
    docs: list[Document] = []
    for path in sorted(docs_dir.glob("**/*")):
        loader = LOADERS.get(path.suffix.lower())
        if loader:
            docs.extend(d for d in loader(path) if d.text.strip())
    return docs
