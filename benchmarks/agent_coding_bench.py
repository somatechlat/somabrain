"""
Agent Coding Benchmark (Synthetic, Real HTTP)
--------------------------------------------

Simulates an agent learning to build a tiny FastAPI app by:
- Seeding relevant "tool" documents
- Running a baseline retrieval (vector-only)
- Persisting a RAG session (vector+wm)
- Measuring improvement via graph-only retrieval after persistence
- Measuring planning improvement by including 'retrieved_with' edges

Outputs a JSON summary and prints a concise table.
"""

from __future__ import annotations

import json
import time
from typing import Dict, List

import httpx


def hit_rate(cands: List[dict], truths: List[str]) -> float:
    got = {str((c.get("payload") or {}).get("task") or "") for c in cands}
    truths = [str(x) for x in truths]
    if not truths:
        return 0.0
    return sum(1 for t in truths if t in got) / float(len(truths))


def plan_hit_rate(items: List[str], truths: List[str]) -> float:
    if not truths:
        return 0.0
    s = set(items)
    return sum(1 for t in truths if t in s) / float(len(truths))


def run(base: str = "http://localhost:9696", tenant: str = "benchdev") -> Dict:
    headers = {"Content-Type": "application/json", "X-Tenant-ID": tenant}
    client = httpx.Client()

    # Seed synthetic "tools" knowledge
    docs = [
        "virtualenv creation for Python",
        "pip usage and requirements.txt",
        "FastAPI routes and response models",
        "uvicorn quickstart hosting local server",
        "pytest basics for API testing",
        "requests/httpx client usage",
    ]
    for d in docs:
        client.post(
            f"{base}/remember",
            headers=headers,
            json={"payload": {"task": d, "memory_type": "episodic", "importance": 1}},
        )

    query = "build a tiny FastAPI app exposing /hello"
    truths = [
        "FastAPI routes and response models",
        "uvicorn quickstart hosting local server",
        "virtualenv creation for Python",
    ]

    # Baseline vector-only
    t0 = time.perf_counter()
    r0 = client.post(
        f"{base}/rag/retrieve",
        headers=headers,
        json={"query": query, "top_k": 5, "retrievers": ["vector"], "persist": False},
    ).json()
    dt0 = time.perf_counter() - t0
    hr0 = hit_rate(r0.get("candidates", []), truths)

    # Persist session
    t1 = time.perf_counter()
    r1 = client.post(
        f"{base}/rag/retrieve",
        headers=headers,
        json={
            "query": query,
            "top_k": 5,
            "retrievers": ["vector", "wm"],
            "persist": True,
        },
    ).json()
    dt1 = time.perf_counter() - t1
    sess = r1.get("session_coord")

    # Graph-only after persist (requires hops >= 1; to reach docs via session, planner uses edges)
    t2 = time.perf_counter()
    r2 = client.post(
        f"{base}/rag/retrieve",
        headers=headers,
        json={"query": query, "top_k": 5, "retrievers": ["graph"], "persist": False},
    ).json()
    dt2 = time.perf_counter() - t2
    hr2 = hit_rate(r2.get("candidates", []), truths)

    # Planning baseline (without retrieved_with)
    p0 = client.post(
        f"{base}/plan/suggest",
        headers=headers,
        json={
            "task_key": query,
            "max_steps": 5,
            "rel_types": ["depends_on", "related"],
        },
    ).json()
    phr0 = plan_hit_rate(p0.get("plan", []), truths)

    # Planning after persist (include rag edges)
    p1 = client.post(
        f"{base}/plan/suggest",
        headers=headers,
        json={
            "task_key": query,
            "max_steps": 5,
            "rel_types": ["rag_session", "retrieved_with", "depends_on", "related"],
        },
    ).json()
    phr1 = plan_hit_rate(p1.get("plan", []), truths)

    out = {
        "query": query,
        "truth_docs": truths,
        "baseline": {
            "latency_s": dt0,
            "hit_rate": hr0,
            "candidates": r0.get("candidates", []),
        },
        "persist": {
            "latency_s": dt1,
            "session_coord": sess,
            "candidates": r1.get("candidates", []),
        },
        "post_persist_graph": {
            "latency_s": dt2,
            "hit_rate": hr2,
            "candidates": r2.get("candidates", []),
        },
        "plan": {
            "baseline": p0.get("plan", []),
            "baseline_hit_rate": phr0,
            "post_persist": p1.get("plan", []),
            "post_persist_hit_rate": phr1,
        },
    }
    return out


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:9696")
    ap.add_argument("--tenant", default="benchdev")
    ap.add_argument("--out", default="benchmarks/results_agent_coding.json")
    args = ap.parse_args()
    res = run(args.base, args.tenant)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    # Print concise table
    print("Agent Coding Bench Results")
    print(
        json.dumps(
            {
                "baseline_vector_hit_rate": res["baseline"]["hit_rate"],
                "persist_mix_latency_s": res["persist"]["latency_s"],
                "post_persist_graph_hit_rate": res["post_persist_graph"]["hit_rate"],
                "plan_baseline_hit_rate": res["plan"]["baseline_hit_rate"],
                "plan_post_persist_hit_rate": res["plan"]["post_persist_hit_rate"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
