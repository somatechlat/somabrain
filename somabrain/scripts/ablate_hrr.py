from __future__ import annotations

import time
import statistics
from typing import Dict, Any

from fastapi.testclient import TestClient

import somabrain.app as appmod


def _bench(client: TestClient, query: str, top_k: int, n: int = 200) -> Dict[str, Any]:
    ts = []
    for _ in range(n):
        t0 = time.perf_counter()
        r = client.post("/recall", json={"query": query, "top_k": top_k})
        r.raise_for_status()
        ts.append(time.perf_counter() - t0)
    p50 = statistics.median(ts)
    p95 = sorted(ts)[int(0.95 * len(ts)) - 1]
    return {"n": n, "p50_ms": round(p50 * 1000, 2), "p95_ms": round(p95 * 1000, 2)}


def main():
    client = TestClient(appmod.app)
    # Ensure HRR enabled if comparing HRR-first
    appmod.cfg.use_hrr = True

    # Scenario A: HRR-first disabled
    appmod.cfg.use_hrr_first = False
    a = _bench(client, query="write docs", top_k=3, n=100)

    # Scenario B: HRR-first enabled (no margin gating)
    appmod.cfg.use_hrr_first = True
    appmod.cfg.hrr_rerank_only_low_margin = False
    b = _bench(client, query="write docs", top_k=3, n=100)

    # Scenario C: HRR-first enabled with margin gating
    appmod.cfg.hrr_rerank_only_low_margin = True
    appmod.cfg.rerank_margin_threshold = 0.05
    c = _bench(client, query="write docs", top_k=3, n=100)

    print({"A_no_hrr": a, "B_hrr": b, "C_hrr_gated": c})


if __name__ == "__main__":
    main()

