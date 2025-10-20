from __future__ import annotations

import time
import statistics
from fastapi.testclient import TestClient

from somabrain.app import app


def bench(n: int = 200, query: str = "hello world", top_k: int = 3):
    client = TestClient(app)
    # Warmup
    client.get("/health")
    ts = []
    for _ in range(n):
        t0 = time.perf_counter()
        r = client.post("/recall", json={"query": query, "top_k": top_k})
        r.raise_for_status()
        ts.append(time.perf_counter() - t0)
    p50 = statistics.median(ts)
    p95 = sorted(ts)[int(0.95 * len(ts)) - 1]
    print({"n": n, "p50_ms": round(p50 * 1000, 2), "p95_ms": round(p95 * 1000, 2)})


if __name__ == "__main__":
    bench()

