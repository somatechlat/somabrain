#!/usr/bin/env python3
"""
Recall Latency Benchmark

Measures p50/p95 latency for simple remember/recall flows against a running
Somabrain API (default http://127.0.0.1:9999) with a memory backend on 9595.

Outputs a JSON summary with basic stats.
"""
from __future__ import annotations

import json
import os
import random
import statistics
import string
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Tuple

import requests

API = os.getenv("SOMA_API_URL", "http://127.0.0.1:9999")
TENANT = os.getenv("SOMA_TENANT", "sandbox")
NAMESPACE = os.getenv("SOMA_NAMESPACE", "public")
N = int(os.getenv("BENCH_N", "200"))
Q = int(os.getenv("BENCH_Q", "50"))
TOPK = int(os.getenv("BENCH_TOPK", "3"))


def _rand_text(k: int = 24) -> str:
    return "".join(random.choice(string.ascii_lowercase + " ") for _ in range(k))


@dataclass
class Sample:
    phase: str
    latency_ms: float
    status: int


@dataclass
class Summary:
    n_remember: int
    n_recall: int
    p50_remember_ms: float
    p95_remember_ms: float
    p50_recall_ms: float
    p95_recall_ms: float
    errors: int


def _post_json(path: str, payload: Dict[str, Any]) -> Tuple[int, float, Dict[str, Any]]:
    url = f"{API}{path}"
    t0 = time.perf_counter()
    r = requests.post(url, json=payload, timeout=5)
    dt = (time.perf_counter() - t0) * 1000.0
    try:
        data = r.json()
    except Exception:
        data = {"_raw": r.text}
    return r.status_code, dt, data


def main() -> None:
    random.seed(42)
    # Remember phase
    remember_lat: List[float] = []
    recall_lat: List[float] = []
    errors = 0

    keys: List[str] = []
    for i in range(N):
        key = f"k{i:06d}"
        keys.append(key)
        payload = {
            "tenant": TENANT,
            "namespace": NAMESPACE,
            "key": key,
            "value": {
                "task": _rand_text(32),
                "fact": _rand_text(16),
                "text": _rand_text(24),
            },
        }
        code, dt, _ = _post_json("/remember", payload)
        if code != 200:
            errors += 1
        remember_lat.append(dt)

    # Recall phase
    for _ in range(Q):
        # Query by a substring of a random remembered value
        k = random.choice(keys)
        needle = random.choice(["task", "fact", "text"])
        # keep query length small to increase hit-rate
        q = _rand_text(6)
        payload = {
            "tenant": TENANT,
            "namespace": NAMESPACE,
            "query": q,
            "top_k": TOPK,
        }
        code, dt, data = _post_json("/recall", payload)
        if code != 200:
            errors += 1
        recall_lat.append(dt)

    def pctl(vals: List[float], p: float) -> float:
        if not vals:
            return 0.0
        return float(statistics.quantiles(vals, n=100)[int(p) - 1])

    summ = Summary(
        n_remember=len(remember_lat),
        n_recall=len(recall_lat),
        p50_remember_ms=pctl(remember_lat, 50),
        p95_remember_ms=pctl(remember_lat, 95),
        p50_recall_ms=pctl(recall_lat, 50),
        p95_recall_ms=pctl(recall_lat, 95),
        errors=errors,
    )
    print(json.dumps(asdict(summ), indent=2))


if __name__ == "__main__":
    main()
