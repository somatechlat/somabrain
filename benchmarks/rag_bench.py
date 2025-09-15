"""
RAG Benchmark: Persistence Benefit and Latency
----------------------------------------------

Measures baseline retrieval quality and latency, then the effect of enabling
session persistence + linking on subsequent graph-based retrieval.

This uses the in-process FastAPI app and the local memory backend.
"""

from __future__ import annotations

import time
from typing import List

from fastapi.testclient import TestClient

from somabrain.app import app


def _remember(client: TestClient, task: str, headers: dict):
    r = client.post(
        "/remember",
        json={"payload": {"task": task, "memory_type": "episodic", "importance": 1}},
        headers=headers,
    )
    assert r.status_code == 200, r.text


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


def run():
    client = TestClient(app)
    headers = {"X-Tenant-ID": "ragbench"}

    # Seed a small corpus
    docs = [
        "solar energy optimization with panels",
        "wind turbine maintenance guide",
        "battery storage for solar microgrids",
        "photovoltaic inverter diagnostics",
        "intro to renewable energy planning",
    ]
    for d in docs:
        _remember(client, d, headers)

    query = "solar energy planning"
    top_k = 5

    # Baseline: vector only, no persist
    t0 = time.perf_counter()
    r0 = client.post(
        "/rag/retrieve",
        headers=headers,
        json={
            "query": query,
            "top_k": top_k,
            "retrievers": ["vector"],
            "persist": False,
        },
    )
    dt0 = time.perf_counter() - t0
    data0 = r0.json()
    hr0 = _hit_rate(data0.get("candidates", []), [docs[0], docs[2]])

    # Persist a session (vector+wm to get some docs and create links)
    t1 = time.perf_counter()
    r1 = client.post(
        "/rag/retrieve",
        headers=headers,
        json={
            "query": query,
            "top_k": top_k,
            "retrievers": ["vector", "wm"],
            "persist": True,
        },
    )
    dt1 = time.perf_counter() - t1
    data1 = r1.json()
    hr1 = _hit_rate(data1.get("candidates", []), [docs[0], docs[2]])

    # After persistence: graph-only retrieval should surface linked docs via session
    t2 = time.perf_counter()
    r2 = client.post(
        "/rag/retrieve",
        headers=headers,
        json={
            "query": query,
            "top_k": top_k,
            "retrievers": ["graph"],
            "persist": False,
        },
    )
    dt2 = time.perf_counter() - t2
    data2 = r2.json()
    hr2 = _hit_rate(data2.get("candidates", []), [docs[0], docs[2]])

    print("RAG Bench Results")
    print(
        {
            "baseline_vector_latency_s": round(dt0, 6),
            "baseline_vector_hit_rate": hr0,
            "persist_mix_latency_s": round(dt1, 6),
            "persist_mix_hit_rate": hr1,
            "post_persist_graph_latency_s": round(dt2, 6),
            "post_persist_graph_hit_rate": hr2,
        }
    )


if __name__ == "__main__":
    run()
