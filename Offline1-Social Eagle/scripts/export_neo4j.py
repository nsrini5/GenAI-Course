"""Push the saved knowledge graph (data/index/graph.json) into Neo4j, or print the Cypher.

    python -m scripts.export_neo4j            # uses NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD
    python -m scripts.export_neo4j --cypher   # prints Cypher to stdout
"""
import argparse

from app import config
from app.pipeline.relations import KnowledgeGraph, Neo4jGraph

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--cypher", action="store_true")
    args = ap.parse_args()
    kg = KnowledgeGraph.load(config.INDEX_DIR)
    if args.cypher or not config.NEO4J_URI:
        print(kg.to_cypher())
    else:
        print(Neo4jGraph().sync(kg))
