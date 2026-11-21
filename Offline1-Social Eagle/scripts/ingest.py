"""CLI: run the 6-stage ingestion pipeline and optionally a test query.

    python -m scripts.ingest
    python -m scripts.ingest --ask "Which services does the Media Processor notify?"
"""
import argparse
import json
import logging

from app.llm import generate
from app.pipeline.run import run_ingest

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ask")
    ap.add_argument("--mode", default="hybrid", choices=["hybrid", "bm25", "dense", "graph"])
    args = ap.parse_args()

    retriever, report = run_ingest()
    print("\n=== Pipeline report ===")
    for s in report:
        print(json.dumps(s))
    if args.ask:
        res = retriever.search(args.ask, mode=args.mode)
        print("\n=== Linked entities ===\n", res["entities"])
        print("\n=== Graph facts ===")
        for f in res["facts"][:8]:
            print(f"  {f['subject']} -[{f['relation']}]-> {f['object']}")
        print("\n=== Top chunks ===")
        for h in res["hits"]:
            print(f"  {h['score']:.4f}  bm25={h['bm25_rank']} dense={h['dense_rank']} graph={h['graph_rank']}  {h['section']}")
        print("\n=== Answer ===\n", generate(args.ask, res["hits"], res["facts"]))
