"""STAGE 6 – Relationship mapping -> knowledge graph (networkx + Neo4j).

Relations (every edge keeps the source chunk id and the evidence sentence):
  Service    -USES->            Technology   tech mentioned in the service's section
  Service    -OWNS->            Table        "Core tables: ..."
  Service    -INTERACTS_WITH->  Service      "notifies Catalog/Streaming services", "Feeds Recommendation Service"
  Layer      -USES->            Technology   Tech Stack (Frontend / Backend / Databases / Infra)
  Technology -STORES->          Data         Data Storage Layout
  Technology -CARRIES->         Event        Message Queue topics
  Feature    -IMPLEMENTED_BY->  Service      feature group <-> service name overlap
  Layer      -HAS_ROUTE->       Route        Next.js pages
  + free-form triples from the LLM when KG_EXTRACTOR=llm

The graph is saved as graph.json (always) and synced to Neo4j when NEO4J_URI is set.
"""
from __future__ import annotations

import json
import logging
import re
from collections import defaultdict
from pathlib import Path

import networkx as nx

from app import config
from app.pipeline.entities import (
    EVENT_RE, ROUTE_RE, SERVICE_RE, TABLES_RE, TECH, EntityIndex, data_items, storage_blocks, techs_in,
)
from app.pipeline.splitter import Chunk

log = logging.getLogger(__name__)
STOP = set("a an and the of for to in on with by or service services free tier".split())
WORD = re.compile(r"[a-z0-9_.]+")


def _stem(w: str) -> str:
    w = w.lower()
    return w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w


def _toks(s: str) -> set[str]:
    return {_stem(t) for t in WORD.findall(s.lower()) if t not in STOP and len(t) > 1}


def _has(text: str, phrase: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", text) is not None


class KnowledgeGraph:
    def __init__(self) -> None:
        self.g = nx.MultiDiGraph()

    # ---------------------------------------------------------------- build
    def add_entities(self, idx: EntityIndex) -> None:
        for e in idx.entities.values():
            self.g.add_node(e.key, name=e.name, type=e.type, aliases=list(e.aliases), chunks=list(e.chunks))

    def node(self, name: str, type_: str, chunk_id: str) -> str:
        key = f"{type_}:{name}"
        if key not in self.g:
            self.g.add_node(key, name=name, type=type_, aliases=[], chunks=[])
        if chunk_id not in self.g.nodes[key]["chunks"]:
            self.g.nodes[key]["chunks"].append(chunk_id)
        return key

    def relate(self, s: str, rel: str, t: str, chunk_id: str, evidence: str) -> None:
        if s == t or s not in self.g or t not in self.g:
            return
        if any(d["rel"] == rel for d in (self.g.get_edge_data(s, t) or {}).values()):
            return
        self.g.add_edge(s, t, rel=rel, chunk=chunk_id, evidence=evidence.strip()[:240])

    # ---------------------------------------------------------------- persistence
    def save(self, d: Path) -> None:
        (d / "graph.json").write_text(json.dumps(nx.node_link_data(self.g, edges="links"), indent=1))

    @classmethod
    def load(cls, d: Path) -> "KnowledgeGraph":
        kg = cls()
        kg.g = nx.node_link_graph(json.loads((d / "graph.json").read_text()), directed=True, multigraph=True, edges="links")
        return kg

    # ---------------------------------------------------------------- query side
    def link_entities(self, query: str) -> list[str]:
        """Map the question to graph nodes by name/alias phrase match (plural-tolerant)."""
        q = query.lower()
        q_stem = " ".join(_stem(t) for t in WORD.findall(q))
        hits = []
        for n, d in self.g.nodes(data=True):
            for a in {d["name"].lower(), *(x.lower() for x in d.get("aliases", []))}:
                if len(a) < 3 or a in STOP or a == "/":
                    continue
                a_stem = " ".join(_stem(t) for t in WORD.findall(a))
                if _has(q, a) or (a_stem and _has(q_stem, a_stem)):
                    hits.append((len(a), n))
                    break
        hits.sort(reverse=True)
        return [n for _, n in hits]

    def neighborhood(self, seeds: list[str], hops: int) -> dict[str, int]:
        if neo4j_enabled():
            try:
                return Neo4jGraph().neighborhood(seeds, hops)
            except Exception as e:
                log.warning("Neo4j neighborhood query failed (%s) – using local graph", e)
        dist = {s: 0 for s in seeds}
        frontier, u = list(seeds), self.g.to_undirected(as_view=True)
        for h in range(1, hops + 1):
            nxt = []
            for n in frontier:
                for m in u.neighbors(n):
                    if m not in dist:
                        dist[m] = h
                        nxt.append(m)
            frontier = nxt
        return dist

    def facts_for(self, seeds: list[str]) -> list[dict]:
        if neo4j_enabled():
            try:
                return Neo4jGraph().facts(seeds)
            except Exception as e:
                log.warning("Neo4j facts query failed (%s) – using local graph", e)
        seedset, facts = set(seeds), []
        for s, t, d in self.g.edges(data=True):
            if s in seedset or t in seedset:
                facts.append({
                    "subject": self.g.nodes[s]["name"], "relation": d["rel"], "object": self.g.nodes[t]["name"],
                    "evidence": d["evidence"], "chunk": d["chunk"], "both": s in seedset and t in seedset,
                })
        return facts

    def search(self, query: str, n: int) -> tuple[list[tuple[str, float]], list[str], list[dict]]:
        """Graph retrieval -> ([(chunk_id, score)], seed entity names, facts)."""
        seeds = self.link_entities(query)
        if not seeds:
            return [], [], []
        scores: dict[str, float] = defaultdict(float)
        for node, dist in self.neighborhood(seeds, config.KG_HOPS).items():
            if node in self.g:
                for cid in self.g.nodes[node]["chunks"]:
                    scores[cid] += 1.0 / (1 + dist)          # seed 1.0, 1-hop 0.5, 2-hop 0.33
        facts = self.facts_for(seeds)
        for f in facts:
            scores[f["chunk"]] += 1.0 if f["both"] else 0.4  # chunk that states the relation
        facts.sort(key=lambda f: not f["both"])
        ranked = sorted(scores.items(), key=lambda kv: -kv[1])[:n]
        return ranked, [self.g.nodes[s]["name"] for s in seeds], facts[: config.KG_MAX_FACTS]

    def entity(self, name: str) -> dict | None:
        cands = [n for n, d in self.g.nodes(data=True) if d["name"].lower() == name.lower()] or self.link_entities(name)[:1]
        if not cands:
            return None
        n, d = cands[0], self.g.nodes[cands[0]]
        return {
            "name": d["name"], "type": d["type"], "aliases": d["aliases"], "chunks": d["chunks"],
            "out": [{"relation": e["rel"], "target": self.g.nodes[t]["name"], "type": self.g.nodes[t]["type"]} for _, t, e in self.g.out_edges(n, data=True)],
            "in": [{"relation": e["rel"], "source": self.g.nodes[s]["name"], "type": self.g.nodes[s]["type"]} for s, _, e in self.g.in_edges(n, data=True)],
        }

    def stats(self) -> dict:
        types, rels = defaultdict(int), defaultdict(int)
        for _, d in self.g.nodes(data=True):
            types[d["type"]] += 1
        for _, _, d in self.g.edges(data=True):
            rels[d["rel"]] += 1
        return {"nodes": self.g.number_of_nodes(), "edges": self.g.number_of_edges(),
                "node_types": dict(types), "relations": dict(rels), "backend": "neo4j" if neo4j_enabled() else "networkx"}

    def to_vis(self) -> dict:
        return {
            "nodes": [{"id": n, "label": d["name"], "group": d["type"]} for n, d in self.g.nodes(data=True)],
            "edges": [{"from": s, "to": t, "label": d["rel"]} for s, t, d in self.g.edges(data=True)],
        }

    def to_cypher(self) -> str:
        def esc(s: str) -> str:
            return s.replace("\\", "\\\\").replace("'", "\\'")
        out = ["CREATE CONSTRAINT entity_key IF NOT EXISTS FOR (e:Entity) REQUIRE e.key IS UNIQUE;"]
        for n, d in self.g.nodes(data=True):
            out.append(f"MERGE (e:Entity {{key:'{esc(n)}'}}) SET e:{d['type']}, e.name='{esc(d['name'])}';")
        for s, t, d in self.g.edges(data=True):
            out.append(f"MATCH (a:Entity {{key:'{esc(s)}'}}),(b:Entity {{key:'{esc(t)}'}}) MERGE (a)-[r:{d['rel']}]->(b) "
                       f"SET r.evidence='{esc(d['evidence'])}', r.chunk='{esc(d['chunk'])}';")
        return "\n".join(out) + "\n"


# ==================================================================== rules
def map_relations(chunks: list[Chunk], idx: EntityIndex) -> KnowledgeGraph:
    kg = KnowledgeGraph()
    kg.add_entities(idx)
    services = {e.key: e for e in idx.of_type("Service")}

    for c in chunks:
        body = c.body
        m = SERVICE_RE.match(c.section)
        svc = f"Service:{m.group(1).strip()}" if m else None

        if svc:
            for line in body.splitlines():
                for t in techs_in(line):
                    kg.relate(svc, "USES", f"Technology:{t}", c.id, line)
            for tm in TABLES_RE.finditer(body):
                for t in filter(None, re.split(r"[,\s]+", tm.group(1))):
                    kg.relate(svc, "OWNS", f"Table:{t}", c.id, tm.group(0))
            for other, e in services.items():
                if other == svc:
                    continue
                for line in body.splitlines():
                    # case-sensitive alias so "user search" doesn't match the Search service
                    if any(re.search(rf"(?<![A-Za-z]){re.escape(a)}(?![a-z])", line) for a in e.aliases):
                        kg.relate(svc, "INTERACTS_WITH", other, c.id, line)

        if c.section.startswith("1. Tech Stack"):
            for header, bullets in storage_blocks(body):
                for b in bullets:
                    for t in techs_in(b):
                        kg.relate(f"Layer:{header[:-1].strip()}", "USES", f"Technology:{t}", c.id, b)

        if c.section.startswith("3. Data Storage"):
            for header, bullets in storage_blocks(body):
                stores = [f"Technology:{t}" for t in techs_in(header)]
                for b in bullets:
                    if "message queue" in header.lower():
                        for ev in EVENT_RE.findall(b):
                            for s in stores:
                                kg.relate(s, "CARRIES", f"Event:{ev}", c.id, f"{header} {ev}")
                    else:
                        for d in data_items(b):
                            for s in stores:
                                kg.relate(s, "STORES", f"Data:{d}", c.id, f"{header} {b}")

        if c.section.startswith("4. Frontend"):
            for rm in ROUTE_RE.finditer(body):
                kg.relate("Layer:Frontend", "HAS_ROUTE", f"Route:{rm.group(1)}", c.id, rm.group(0))

    for f in idx.of_type("Feature"):
        ft = _toks(f.aliases[0] if f.aliases else f.name)
        for skey, s in services.items():
            if ft & _toks(" ".join(s.aliases)):
                kg.relate(f.key, "IMPLEMENTED_BY", skey, f.chunks[0], f"Feature '{f.name}' is delivered by {s.name}")

    if config.KG_EXTRACTOR == "llm" and config.LLM_PROVIDER != "none":
        _llm_triples(kg, chunks)
    return kg


LLM_PROMPT = (
    "Extract a knowledge graph from the passage. Return ONLY JSON: "
    '{"triples":[{"subject":"","subject_type":"","relation":"","object":"","object_type":""}]}. '
    "Types: Service, Technology, Table, Event, Feature, Data, Route, Layer, Concept. "
    "Relations in UPPER_SNAKE_CASE (USES, OWNS, STORES, PUBLISHES, CONSUMES, DEPENDS_ON...).\n\nPassage:\n"
)


def _llm_triples(kg: KnowledgeGraph, chunks: list[Chunk]) -> None:
    from app.llm import complete

    for c in chunks:
        try:
            raw = complete(LLM_PROMPT + c.text, system="You output strict JSON only.")
            for t in json.loads(raw[raw.index("{"): raw.rindex("}") + 1]).get("triples", []):
                rel = re.sub(r"[^A-Z_]", "", t["relation"].upper().replace(" ", "_")) or "RELATED_TO"
                s = kg.node(t["subject"], re.sub(r"\W", "", t.get("subject_type") or "Concept") or "Concept", c.id)
                o = kg.node(t["object"], re.sub(r"\W", "", t.get("object_type") or "Concept") or "Concept", c.id)
                kg.relate(s, rel, o, c.id, f"{t['subject']} {rel} {t['object']}")
        except Exception as e:
            log.warning("LLM triple extraction failed on %s: %s", c.id, e)


# ==================================================================== Neo4j
def neo4j_enabled() -> bool:
    return bool(config.NEO4J_URI)


class Neo4jGraph:
    """Graph store in Neo4j. Nodes: (:Entity:<Type> {key,name,aliases,chunks}); edges keep evidence + chunk."""

    _driver = None

    def __init__(self):
        if Neo4jGraph._driver is None:
            from neo4j import GraphDatabase

            Neo4jGraph._driver = GraphDatabase.driver(
                config.NEO4J_URI, auth=(config.NEO4J_USER, config.NEO4J_PASSWORD),
                notifications_min_severity="OFF",   # silence "property does not exist" style hints
            )
        self.driver = Neo4jGraph._driver

    def sync(self, kg: KnowledgeGraph, retries: int = 10) -> dict:
        import time

        for attempt in range(retries):
            try:
                return self._sync(kg)
            except Exception as e:
                log.warning("Neo4j sync attempt %d/%d failed: %s", attempt + 1, retries, e)
                time.sleep(3)
        log.error("Neo4j unreachable – graph kept locally (graph.json); retrieval uses networkx")
        return {"neo4j_error": "unreachable"}

    def _sync(self, kg: KnowledgeGraph) -> dict:
        nodes = [{"key": n, "name": d["name"], "type": d["type"], "aliases": d["aliases"], "chunks": d["chunks"]}
                 for n, d in kg.g.nodes(data=True)]
        edges = [{"s": s, "t": t, "rel": d["rel"], "evidence": d["evidence"], "chunk": d["chunk"]}
                 for s, t, d in kg.g.edges(data=True)]
        with self.driver.session(database=config.NEO4J_DATABASE) as ses:
            ses.run("CREATE CONSTRAINT entity_key IF NOT EXISTS FOR (e:Entity) REQUIRE e.key IS UNIQUE")
            ses.run("MATCH (e:Entity) DETACH DELETE e")
            for type_ in {n["type"] for n in nodes}:
                # labels can't be parameterised; type_ is sanitised to \w+ upstream
                ses.run(f"UNWIND $rows AS r MERGE (e:Entity {{key:r.key}}) SET e:`{type_}`, "
                        "e.name=r.name, e.type=r.type, e.aliases=r.aliases, e.chunks=r.chunks",
                        rows=[n for n in nodes if n["type"] == type_])
            for rel in {e["rel"] for e in edges}:
                ses.run(f"UNWIND $rows AS r MATCH (a:Entity {{key:r.s}}), (b:Entity {{key:r.t}}) "
                        f"MERGE (a)-[x:`{rel}`]->(b) SET x.evidence=r.evidence, x.chunk=r.chunk",
                        rows=[e for e in edges if e["rel"] == rel])
        return {"neo4j_nodes": len(nodes), "neo4j_edges": len(edges)}

    def neighborhood(self, seeds: list[str], hops: int) -> dict[str, int]:
        q = (f"MATCH (s:Entity) WHERE s.key IN $seeds "
             f"OPTIONAL MATCH p=(s)-[*1..{max(1, hops)}]-(m:Entity) "
             "WITH s, m, min(length(p)) AS d RETURN s.key AS s, m.key AS m, d")
        dist = {s: 0 for s in seeds}
        with self.driver.session(database=config.NEO4J_DATABASE) as ses:
            for r in ses.run(q, seeds=seeds):
                if r["m"] and (r["m"] not in dist or r["d"] < dist[r["m"]]):
                    dist[r["m"]] = r["d"]
        return dist

    def facts(self, seeds: list[str]) -> list[dict]:
        q = ("MATCH (a:Entity)-[r]->(b:Entity) WHERE a.key IN $seeds OR b.key IN $seeds "
             "RETURN a.name AS subject, type(r) AS relation, b.name AS object, r.evidence AS evidence, "
             "r.chunk AS chunk, (a.key IN $seeds AND b.key IN $seeds) AS both_seeds")
        with self.driver.session(database=config.NEO4J_DATABASE) as ses:
            return [{**dict(r), "both": r["both_seeds"]} for r in ses.run(q, seeds=seeds)]

    def count(self) -> int:
        with self.driver.session(database=config.NEO4J_DATABASE) as ses:
            return ses.run("MATCH (e:Entity) RETURN count(e) AS n").single()["n"]

    def ping(self) -> bool:
        try:
            self.driver.verify_connectivity()
            return True
        except Exception:
            return False
