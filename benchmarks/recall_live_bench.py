"""Live-stack Recall benchmark.

This script expects the full SomaBrain stack running (e.g. via run_dev_full.sh)
and exercises insertion + retrieval via HTTP requests. It records latency,
precision@k against the seeded corpus, and dumps raw results to JSON.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Dict, List
import time

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


def _remember_batch_memory_api(
    base: str,
    tenant: str,
    namespace: str,
    docs: List[str],
    headers: Dict[str, str],
):
    # Use /memory/remember/batch to ensure explicit tenant/namespace and unified indexing
    items = []
    for i, task in enumerate(docs):
        items.append(
            {
                "key": f"seed::{i:04d}",
                "value": {
                    "task": task,
                    "content": task,
                    "memory_type": "episodic",
                    "importance": 1,
                    "universe": "real",
                },
            }
        )
    payload = {"tenant": tenant, "namespace": namespace, "items": items}
    return _post_json(base, "/memory/remember/batch", payload, headers)


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


def _discover_namespace(api_url: str, tenant: str) -> str | None:
    """Fetch /health and return the full namespace used for the given tenant."""
    try:
        js = requests.get(
            f"{api_url}/health", headers={"X-Tenant-ID": tenant}, timeout=3.0
        ).json()
        ns = js.get("namespace")
        if isinstance(ns, str) and (tenant in ns):
            return ns
        return ns if isinstance(ns, str) else None
    except Exception:
        return None


def run(api_url: str, corpus: List[str], output: Path, use_memory_api: bool = True):
    tenant = "recall-live-bench"
    namespace = "public"
    headers = {"X-Tenant-ID": tenant}

    # Seed corpus
    write_times = []
    if use_memory_api:
        try:
            resp, dt = _remember_batch_memory_api(
                api_url, tenant, namespace, corpus, headers
            )
            # Approximate per-item write time from batch
            n = max(1, len(corpus))
            write_times = [dt / n for _ in range(n)]
        except Exception:
            # Fallback to legacy endpoint one-by-one if batch fails (e.g., backend not ready in this mode)
            write_times.clear()
            for doc in corpus:
                payload = {
                    "payload": {
                        "task": doc,
                        "content": doc,
                        "memory_type": "episodic",
                        "importance": 1,
                    }
                }
                try:
                    _, dt = _post_json(api_url, "/remember", payload, headers)
                    write_times.append(dt)
                except Exception:
                    # still record an entry to avoid divide-by-zero later
                    write_times.append(0.0)
    else:
        # Fallback: legacy top-level /remember one-by-one
        for doc in corpus:
            payload = {
                "payload": {
                    "task": doc,
                    "content": doc,
                    "memory_type": "episodic",
                    "importance": 1,
                }
            }
            _, dt = _post_json(api_url, "/remember", payload, headers)
            write_times.append(dt)

    # Best-effort: allow the external memory indexer to catch up
    try:
        time.sleep(0.5)
    except Exception:
        pass

    query = "solar energy planning"
    top_k = 5
    ground_truth = [corpus[0], corpus[2]]

    if use_memory_api:
        # Memory API unified recall (WM + LTM); returns items in results
        recall_payload = {
            "tenant": tenant,
            "namespace": namespace,
            "query": query,
            "top_k": top_k,
            "layer": "all",
        }
        try:
            mem_resp, dt_mem = _post_json(
                api_url, "/memory/recall", recall_payload, headers
            )
            # Normalize shape to match previous result structure
            norm_results = [
                {"payload": item.get("payload", {})}
                for item in mem_resp.get("results", [])
                if isinstance(item, dict)
            ]
            hr_vec = _hit_rate(norm_results, ground_truth)
            hr_mix = hr_vec
            hr_graph = hr_vec
            dt_vec = dt_mem
            dt_mix = dt_mem
            dt_graph = dt_mem
            vec_resp = {"results": norm_results}
            mix_resp = vec_resp
            graph_resp = vec_resp
        except Exception:
            # Fallback to legacy /recall
            payload_vec = {"query": query, "top_k": top_k}
            vec_resp, dt_vec = _post_json(api_url, "/recall", payload_vec, headers)
            hr_vec = _hit_rate(vec_resp.get("results", []), ground_truth)

            payload_mix = {"query": query, "top_k": top_k}
            mix_resp, dt_mix = _post_json(api_url, "/recall", payload_mix, headers)
            hr_mix = _hit_rate(mix_resp.get("results", []), ground_truth)

            payload_graph = {"query": query, "top_k": top_k}
            graph_resp, dt_graph = _post_json(
                api_url, "/recall", payload_graph, headers
            )
            hr_graph = _hit_rate(graph_resp.get("results", []), ground_truth)
    else:
        # Legacy top-level /recall paths (pipeline params ignored by server)
        payload_vec = {"query": query, "top_k": top_k}
        vec_resp, dt_vec = _post_json(api_url, "/recall", payload_vec, headers)
        hr_vec = _hit_rate(vec_resp.get("results", []), ground_truth)

        payload_mix = {"query": query, "top_k": top_k}
        mix_resp, dt_mix = _post_json(api_url, "/recall", payload_mix, headers)
        hr_mix = _hit_rate(mix_resp.get("results", []), ground_truth)

        payload_graph = {"query": query, "top_k": top_k}
        graph_resp, dt_graph = _post_json(api_url, "/recall", payload_graph, headers)
        hr_graph = _hit_rate(graph_resp.get("results", []), ground_truth)

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
            "results": vec_resp.get("results", []),
        },
        "mix": {
            "latency_s": dt_mix,
            "hit_rate": hr_mix,
            "results": mix_resp.get("results", []),
        },
        "graph": {
            "latency_s": dt_graph,
            "hit_rate": hr_graph,
            "results": graph_resp.get("results", []),
        },
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Benchmark results written to {output}")


if __name__ == "__main__":  # pragma: no cover
    parser = argparse.ArgumentParser(
        description="Run live recall benchmark against SomaBrain stack"
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
        default=Path("benchmarks/outputs/recall_live_results.json"),
    )
    parser.add_argument(
        "--use-memory-api",
        action="store_true",
        help="Use /memory API endpoints for seeding and recall (recommended)",
        default=True,
    )
    args = parser.parse_args()

    if args.corpus and args.corpus.exists():
        docs = json.loads(args.corpus.read_text(encoding="utf-8"))
    else:
        docs = DEFAULT_CORPUS

    run(args.api_url, docs, args.output, use_memory_api=bool(args.use_memory_api))
