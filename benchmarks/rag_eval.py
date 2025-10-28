"""
RAG Evaluation Harness
----------------------

Evaluates the RAG pipeline on a small curated set and reports:
- Recall@k, MRR, NDCG (approx), and latency breakdowns per stage.

Usage:
    python benchmarks/rag_eval.py --k 5 --persist --tenant eval
"""

from __future__ import annotations

import argparse
import time
from typing import List, Tuple

from fastapi.testclient import TestClient

from somabrain.app import app


def _hit_rate(candidates: List[dict], truths: List[str]) -> float:
    got = set()
    for c in candidates:
        p = c.get("payload", {})
        t = p.get("task") or p.get("fact")
        if t:
            got.add(str(t))
    truths = [str(x) for x in truths]
    if not truths:
        return 0.0
    return len([t for t in truths if t in got]) / float(len(truths))


def _mrr(candidates: List[dict], truths: List[str]) -> float:
    truthset = [str(x) for x in truths]
    for i, c in enumerate(candidates, start=1):
        t = str(
            c.get("payload", {}).get("task") or c.get("payload", {}).get("fact") or ""
        )
        if t and t in truthset:
            return 1.0 / float(i)
    return 0.0


def _ndcg(candidates: List[dict], truths: List[str]) -> float:
    import math

    truthset = [str(x) for x in truths]
    dcg = 0.0
    for i, c in enumerate(candidates, start=1):
        t = str(
            c.get("payload", {}).get("task") or c.get("payload", {}).get("fact") or ""
        )
        rel = 1.0 if t and t in truthset else 0.0
        dcg += rel / math.log2(i + 1.0)
    # ideal DCG
    n = min(len(truths), len(candidates))
    idcg = sum(1.0 / math.log2(i + 1.0) for i in range(1, n + 1))
    return float(dcg / idcg) if idcg > 0 else 0.0


def _remember(client: TestClient, task: str, headers: dict):
    r = client.post(
        "/remember",
        json={"payload": {"task": task, "memory_type": "episodic", "importance": 1}},
        headers=headers,
    )
    assert r.status_code == 200, r.text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--tenant", type=str, default="eval")
    ap.add_argument("--persist", action="store_true")
    args = ap.parse_args()

    client = TestClient(app)
    headers = {"X-Tenant-ID": args.tenant}

    # Seed small corpus
    docs = [
        "solar energy optimization with panels",
        "wind turbine maintenance guide",
        "battery storage for solar microgrids",
        "photovoltaic inverter diagnostics",
        "intro to renewable energy planning",
    ]
    for d in docs:
        _remember(client, d, headers)

    query_truths: List[Tuple[str, List[str]]] = [
        ("solar energy planning", [docs[0], docs[2]]),
        ("wind maintenance", [docs[1]]),
        ("inverter diagnostics", [docs[3]]),
    ]

    metrics = []
    for q, truths in query_truths:
        t0 = time.perf_counter()
        r = client.post(
            "/recall",
            headers=headers,
            json={
                "query": q,
                "top_k": args.k,
                "retrievers": ["vector", "lexical", "wm", "graph"],
                "persist": bool(args.persist),
                "rerank": "ce",
            },
        )
        dt = time.perf_counter() - t0
        assert r.status_code == 200, r.text
        data = r.json()
        cands = data.get("results", [])
        metrics.append(
            {
                "query": q,
                "recall@k": _hit_rate(cands, truths),
                "mrr": _mrr(cands, truths),
                "ndcg": _ndcg(cands, truths),
                "latency_s": round(dt, 6),
            }
        )

    from pprint import pprint

    print("RAG Eval Summary:")
    pprint(metrics)


if __name__ == "__main__":
    main()
