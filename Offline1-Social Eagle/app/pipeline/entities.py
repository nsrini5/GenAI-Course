"""STAGE 5 – Entity extraction.

Rule-based extractor (deterministic, free) tuned to software-architecture documents.
Entity types produced:
  Service     – "14) Media Processor Service"            (from section headings)
  Feature     – "B. Playback & Player"                   (feature checklist headings)
  Technology  – PostgreSQL, Kafka, FFmpeg, Next.js ...    (gazetteer, alias-aware)
  Table       – playlist_tracks, ad_impressions ...       ("Core tables: ..." lines)
  Event       – track_uploaded, playback_event ...        (message-queue topics)
  Data        – "hls segments", "playback events" ...     (Data Storage Layout bullets)
  Layer       – Frontend, Backend, Databases & Storage... (Tech Stack headings)
  Route       – /home, /playlist/:id ...                  (Next.js routes)
With KG_EXTRACTOR=llm, the LLM adds further entities in the relationship stage.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from app.pipeline.splitter import Chunk

TECH: dict[str, list[str]] = {
    "Next.js": ["next.js", "nextjs"], "React": ["react"], "TypeScript": ["typescript"],
    "Tailwind CSS": ["tailwind"], "Radix UI": ["radix"], "Headless UI": ["headless ui"],
    "React Query": ["react query", "tanstack query"], "Zustand": ["zustand"], "Recoil": ["recoil"],
    "Jotai": ["jotai"], "HLS.js": ["hls.js"], "Web Audio API": ["web audio api", "html5 audio"],
    "OAuth2/OIDC": ["oauth2", "oidc"], "PWA": ["pwa"], "Node.js": ["node.js", "nodejs"],
    "NestJS": ["nestjs"], "REST": ["rest"], "gRPC": ["grpc"], "Kafka": ["kafka"], "NATS": ["nats"],
    "RabbitMQ": ["rabbitmq"], "Nginx": ["nginx"], "Envoy": ["envoy"], "Kong": ["kong"],
    "PostgreSQL": ["postgresql", "postgres"], "Redis": ["redis"],
    "Elasticsearch/OpenSearch": ["elasticsearch", "opensearch"], "ClickHouse": ["clickhouse", "data warehouse"],
    "S3 Object Storage": ["s3", "object storage"], "CDN": ["cdn", "cloudfront", "fastly", "cloudflare"],
    "Docker": ["docker"], "Kubernetes": ["kubernetes", "gke", "eks", "aks"],
    "Vault": ["vault", "secrets manager"], "GitHub Actions": ["github actions"], "GitLab CI": ["gitlab ci"],
    "Prometheus": ["prometheus"], "Grafana": ["grafana"], "OpenTelemetry": ["opentelemetry"],
    "FFmpeg": ["ffmpeg"], "Stripe": ["stripe"], "Razorpay": ["razorpay"], "WebSocket": ["websocket"],
    "JWT": ["jwt"], "HLS": ["hls"],
}

SERVICE_RE = re.compile(r"^2\. Microservices.*?>\s*\d+\)\s*(.+)$")
FEATURE_RE = re.compile(r"^5\. Feature Checklist.*?>\s*([A-M])\.\s*(.+)$")
TABLES_RE = re.compile(r"Core tables:\s*([a-z_,\s]+)")
ROUTE_RE = re.compile(r"(?m)^\s*-?\s*(/[a-z][\w/:\-]*|/)\s*(?:→\s*(.+))?$")
EVENT_RE = re.compile(r"\b[a-z]+_[a-z_]+\b")


def has_word(text_lower: str, alias: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", text_lower) is not None


def techs_in(line: str) -> list[str]:
    low = line.lower()
    return [t for t, al in TECH.items() if any(has_word(low, a) for a in al)]


def service_aliases(title: str) -> list[str]:
    base = re.sub(r"\bService\b", "", title)
    return [p.strip() for p in re.split(r"/|&|\(|\)", base) if len(p.strip()) > 2]


def storage_blocks(body: str):
    """Yield (header_line, [bullet_lines]) for 'PostgreSQL:' style blocks."""
    header, bullets = None, []
    for line in body.splitlines():
        if line.endswith(":") and not line.startswith("-"):
            if header:
                yield header, bullets
            header, bullets = line, []
        elif header and line.startswith("-"):
            bullets.append(line)
        elif header and bullets:
            bullets[-1] += " " + line          # wrapped bullet
    if header:
        yield header, bullets


def data_items(bullet: str) -> list[str]:
    text = re.sub(r"\(.*?\)|\(.*$", "", bullet.lstrip("- ")).rstrip(". ")
    text = re.sub(r"^[A-Za-z ]+:\s*", "", text)   # "Aggregations: daily..." -> "daily..."
    out = []
    for piece in re.split(r",\s*|\band\b", text):
        p = piece.strip(" .").lower()
        if 2 < len(p) <= 40 and p not in {"etc", "etc."} and not EVENT_RE.search(p):
            out.append(p)
    return out


@dataclass
class Entity:
    key: str
    name: str
    type: str
    aliases: list[str] = field(default_factory=list)
    chunks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class EntityIndex:
    def __init__(self) -> None:
        self.entities: dict[str, Entity] = {}

    def add(self, name: str, type_: str, chunk_id: str | None = None, aliases: list[str] | None = None) -> str:
        key = f"{type_}:{name}"
        e = self.entities.get(key)
        if e is None:
            e = self.entities[key] = Entity(key, name, type_)
        for a in aliases or []:
            if a and a not in e.aliases:
                e.aliases.append(a)
        if chunk_id and chunk_id not in e.chunks:
            e.chunks.append(chunk_id)
        return key

    def of_type(self, type_: str) -> list[Entity]:
        return [e for e in self.entities.values() if e.type == type_]

    def __len__(self) -> int:
        return len(self.entities)


def extract_entities(chunks: list[Chunk]) -> EntityIndex:
    idx = EntityIndex()
    for c in chunks:
        body = c.body
        if m := SERVICE_RE.match(c.section):
            title = m.group(1).strip()
            idx.add(title, "Service", c.id, service_aliases(title))
        elif m := FEATURE_RE.match(c.section):
            idx.add(f"{m.group(1)}. {m.group(2).strip()}", "Feature", c.id, [m.group(2).strip()])

        for line in body.splitlines():
            for t in techs_in(line):
                idx.add(t, "Technology", c.id, TECH[t])

        for m in TABLES_RE.finditer(body):
            for t in filter(None, re.split(r"[,\s]+", m.group(1))):
                idx.add(t, "Table", c.id)

        if c.section.startswith("1. Tech Stack"):
            for header, _ in storage_blocks(body):
                idx.add(header[:-1].strip(), "Layer", c.id)

        if c.section.startswith("3. Data Storage"):
            for header, bullets in storage_blocks(body):
                if "message queue" in header.lower():
                    for b in bullets:
                        for ev in EVENT_RE.findall(b):
                            idx.add(ev, "Event", c.id)
                else:
                    for b in bullets:
                        for d in data_items(b):
                            idx.add(d, "Data", c.id)

        if c.section.startswith("4. Frontend"):
            idx.add("Frontend", "Layer", c.id)
            for m in ROUTE_RE.finditer(body):
                idx.add(m.group(1), "Route", c.id, [m.group(2).strip(" .")] if m.group(2) else None)
    return idx
