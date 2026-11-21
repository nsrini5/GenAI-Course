"""STAGE 2 – Text splitter (section-aware, recursive).

1. Detect headings ("2. Microservices", "7) Playback & Session Service", "B. Playback & Player")
   and split the document into sections, keeping a breadcrumb title
   e.g. "2. Microservices (High-Level) > 14) Media Processor Service".
2. Sections longer than CHUNK_SIZE are windowed on line boundaries with CHUNK_OVERLAP.
3. Each chunk is prefixed with its section title so both BM25 and the embedding
   model see the topic, and the entity extractor knows which service it belongs to.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass

from app import config
from app.pipeline.loader import Document

HEADING_RE = re.compile(r"^\s*(\d{1,2}[.)]|[A-M]\.)\s+[A-Z][^\n]{2,80}$")
UNDERLINE_RE = re.compile(r"^\s*[-=]{4,}\s*$")


@dataclass
class Chunk:
    id: str
    source: str
    section: str
    page: int
    text: str

    @property
    def body(self) -> str:
        return self.text.split("\n", 1)[1] if "\n" in self.text else self.text

    def to_dict(self) -> dict:
        return asdict(self)


def _sections(docs: list[Document]) -> list[tuple[str, str, int, str]]:
    """-> [(source, section_title, first_page, body)]"""
    out: list[tuple[str, str, int, str]] = []
    by_source: dict[str, list[Document]] = {}
    for d in docs:
        by_source.setdefault(d.metadata["source"], []).append(d)

    for source, pages in by_source.items():
        top = current = "Overview"
        page_of, buf = 1, []

        def flush():
            body = "\n".join(buf).strip()
            if body:
                out.append((source, current, page_of, body))

        for d in pages:
            for raw in d.text.splitlines():
                line = raw.strip()
                if not line or UNDERLINE_RE.match(line):
                    continue
                if HEADING_RE.match(line):
                    flush()
                    buf = []
                    if re.match(r"^\d{1,2}\.\s", line):
                        top = current = line
                    else:
                        current = f"{top} > {line}"
                    page_of = d.metadata["page"]
                    continue
                buf.append(line)
        flush()
    return out


def _window(text: str, size: int, overlap: int) -> list[str]:
    if len(text) <= size:
        return [text]
    out, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        cut = text.rfind("\n", start + size // 2, end)
        if end < len(text) and cut != -1:
            end = cut
        out.append(text[start:end].strip())
        if end >= len(text):
            break
        nxt = max(end - overlap, start + 1)
        nl = text.find("\n", nxt, end)
        start = nl + 1 if nl != -1 else nxt
    return [c for c in out if c]


def split_documents(docs: list[Document]) -> list[Chunk]:
    chunks: list[Chunk] = []
    for s_idx, (source, title, page, body) in enumerate(_sections(docs)):
        stem = source.rsplit(".", 1)[0]
        for w_idx, piece in enumerate(_window(body, config.CHUNK_SIZE, config.CHUNK_OVERLAP)):
            chunks.append(Chunk(f"{stem}-{s_idx:03d}-{w_idx:02d}", source, title, page, f"{title}\n{piece}"))
    return chunks
