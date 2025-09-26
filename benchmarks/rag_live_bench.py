"""Live-stack RAG benchmark.

This script expects the full SomaBrain stack running (e.g. via run_dev_full.sh)
and exercises insertion + retrieval via HTTP requests. It records latency,
precision@k against the seeded corpus, and dumps raw results + metrics to JSON.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Dict, List

import requests
from prometheus_client.parser import text_string_to_metric_families

DEFAULT_CORPUS = [
    "solar energy optimization with panels",
    "wind turbine maintenance guide",
    "battery storage for solar microgrids",
    "photovoltaic inverter diagnostics",
    "intro to renewable energy planning",
    "microgrid load balancing tutorial",
    "renewable energy policy checklist",
    "grid resilience analytics playbook",
]


def _post_json(
    base: str, path: str, payload: dict, headers: Dict[str, str], timeout: float = 5.0
):
    url = base.rstrip("/") + path
    resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
    resp.raise_for_status()
    return resp.json(), resp.elapsed.total_seconds()


def _remember(base: str, task: str, headers: Dict[str, str]):
    payload = {
        "payload": {
            "task": task,
            "memory_type": "episodic",
            "importance": 1,
        }
    }
    return _post_json(base, "/remember", payload, headers)


def _hit_rate(candidates: List[dict], truths: List[str]) -> float:
    got = set()
    for c in candidates:
        payload = c.get("payload") or {}
        task = payload.get("task") or payload.get("fact")
        if task:
            got.add(str(task))
    truths = [str(x) for x in truths]
    if not truths:
        return 0.0
    return sum(1 for t in truths if t in got) / float(len(truths))


def _metric_value(
    metrics_text: str, metric: str, labels: Dict[str, str] | None = None
) -> float:
    labels = labels or {}
    for family in text_string_to_metric_families(metrics_text):
        if family.name != metric:
            continue
        for sample in family.samples:
            if sample.name != metric:
                continue
            sample_labels = sample.labels or {}
            if all(sample_labels.get(k) == v for k, v in labels.items()):
                return float(sample.value)
    return 0.0


def run(api_url: str, corpus: List[str], output: Path):
    headers = {"X-Tenant-ID": "rag-live-bench"}

    # Seed corpus via live API
    write_times = []
    for doc in corpus:
        _, dt = _remember(api_url, doc, headers)
        write_times.append(dt)

    query = "solar energy planning"
    top_k = 5
    ground_truth = [corpus[0], corpus[2]]

    metrics_before = requests.get(f"{api_url}/metrics", timeout=5.0).text
    rag_total_before = _metric_value(metrics_before, "somabrain_rag_requests_total", {})

    # Vector only
    payload_vec = {
        "query": query,
        "top_k": top_k,
        "retrievers": ["vector"],
        "persist": False,
    }
    vec_resp, dt_vec = _post_json(api_url, "/rag/retrieve", payload_vec, headers)
    hr_vec = _hit_rate(vec_resp.get("candidates", []), ground_truth)

    # Mixed vector + WM with persistence
    payload_mix = {
        "query": query,
        "top_k": top_k,
        "retrievers": ["vector", "wm"],
        "persist": True,
    }
    mix_resp, dt_mix = _post_json(api_url, "/rag/retrieve", payload_mix, headers)
    hr_mix = _hit_rate(mix_resp.get("candidates", []), ground_truth)

    # Graph-only after persistence
    payload_graph = {
        "query": query,
        "top_k": top_k,
        "retrievers": ["graph"],
        "persist": False,
    }
    graph_resp, dt_graph = _post_json(api_url, "/rag/retrieve", payload_graph, headers)
    hr_graph = _hit_rate(graph_resp.get("candidates", []), ground_truth)

    metrics_after = requests.get(f"{api_url}/metrics", timeout=5.0).text
    rag_total_after = _metric_value(metrics_after, "somabrain_rag_requests_total", {})

    results = {
        "api_url": api_url,
        "tenant": headers["X-Tenant-ID"],
        "seed_count": len(corpus),
        "write_latency_s": {
            "avg": sum(write_times) / len(write_times),
            "p95": sorted(write_times)[int(0.95 * len(write_times)) - 1],
        },
        "vector": {
            "latency_s": dt_vec,
            "hit_rate": hr_vec,
            "candidates": vec_resp.get("candidates", []),
        },
        "mix": {
            "latency_s": dt_mix,
            "hit_rate": hr_mix,
            "candidates": mix_resp.get("candidates", []),
        },
        "graph": {
            "latency_s": dt_graph,
            "hit_rate": hr_graph,
            "candidates": graph_resp.get("candidates", []),
        },
        "rag_requests_total_before": rag_total_before,
        "rag_requests_total_after": rag_total_after,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Benchmark results written to {output}")


if __name__ == "__main__":  # pragma: no cover
    parser = argparse.ArgumentParser(
        description="Run live RAG benchmark against SomaBrain stack"
    )
    parser.add_argument(
        "--api-url", default=os.getenv("SOMABRAIN_API_URL", "http://127.0.0.1:9696")
    )
    parser.add_argument(
        "--corpus",
        type=Path,
        help="Optional JSON file containing list of documents",
        default=None,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("benchmarks/outputs/rag_live_results.json"),
    )
    args = parser.parse_args()

    if args.corpus and args.corpus.exists():
        docs = json.loads(args.corpus.read_text(encoding="utf-8"))
    else:
        docs = DEFAULT_CORPUS

    run(args.api_url, docs, args.output)
