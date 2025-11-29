"""Small harness: POST 100 /remember concurrently, then /recall.

Usage (from repo root):
    python3 benchmarks/scale/run_remember_recall.py

It reads SOMABRAIN_HOST_PORT from .env if present, otherwise defaults to 9696.
Sends minimal valid RememberRequest bodies and then queries /recall.
"""

from __future__ import annotations

import asyncio

# Removed direct os import; using centralized settings for environment variables.
import statistics
import time

import httpx
import uuid

# Config
ENV_FILE = ".env"
DEFAULT_PORT = 9696


def read_env_port() -> int:
    port = None
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r") as f:
            for line in f:
                if line.strip().startswith("SOMABRAIN_HOST_PORT="):
                    _, v = line.strip().split("=", 1)
                    try:
                        port = int(v)
                    except Exception as exc: raise
    return port or DEFAULT_PORT


from common.config.settings import settings

API_PORT = read_env_port()
BASE = settings.api_url

HEADERS = {"Content-Type": "application/json"}


def make_payload(i: int):
    return {
        "payload": {
            "task": "scale-test",
            "importance": 1,
            "memory_type": "episodic",
            "timestamp": time.time(),
            "who": "bench",
            "did": f"action-{i}",
            "what": "scale-memory",
            "where": "bench-suite",
            "why": "load-test",
        }
    }


async def post_remember(client: httpx.AsyncClient, i: int):
    """Post a single /remember with configurable timeout via BENCH_TIMEOUT env var (seconds).

    Adds a unique X-Request-ID header so the server logs can be correlated.
    Returns a tuple including the generated request id.
    """
    body = make_payload(i)
    start = time.perf_counter()
    bench_timeout = float(settings.bench_timeout)
    rid = f"bench-{i}-{int(time.time() * 1000)}-{uuid.uuid4().hex[:6]}"
    hdrs = dict(HEADERS)
    hdrs["X-Request-ID"] = rid
    try:
        r = await client.post(
            "/remember", json=body, headers=hdrs, timeout=bench_timeout
        )
        elapsed = (time.perf_counter() - start) * 1000.0
        return (i, rid, r.status_code, r.text[:200], elapsed)
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000.0
        return (i, rid, 0, repr(e), elapsed)


async def run():
    async with httpx.AsyncClient(base_url=BASE) as client:
        tasks = [post_remember(client, i) for i in range(100)]
        print(f"Posting 100 /remember to {BASE}/remember ...")
        results = await asyncio.gather(*tasks)

        # results are (i, rid, status, excerpt_or_err, elapsed_ms)
        codes = [r[2] for r in results]
        times = [r[4] for r in results]
        ok = sum(1 for c in codes if c == 200)
        print(f"Remember results: {ok}/100 OK")
        print(
            f"Latency ms: mean={statistics.mean(times):.1f} median={statistics.median(times):.1f} p95={statistics.quantiles(times, n=100)[94]:.1f}"
        )

        # Dump per-request mapping lines to aid correlation with server logs
        for r in results:
            i, rid, status, excerpt, elapsed = r
            print(f"RID,{i},{rid},{status},{elapsed:.1f}")

        # Now a /recall likely matching the "scale-memory" items
        print("Waiting 0.5s for async persistence...")
        await asyncio.sleep(0.5)
        qstart = time.perf_counter()
        try:
            r = await client.post(
                "/recall",
                json={"query": "scale-memory", "top_k": 10},
                headers=HEADERS,
                timeout=20.0,
            )
            qtime = (time.perf_counter() - qstart) * 1000.0
            print(f"Recall status={r.status_code} time_ms={qtime:.1f}")
            if r.status_code == 200:
                j = r.json()
                print(
                    f"Recall wm hits: {len(j.get('wm', []))} memory hits: {len(j.get('memory', []))}"
                )
            else:
                print(r.text)
        except Exception as e:
            print("Recall failed:", e)


if __name__ == "__main__":
    asyncio.run(run())
