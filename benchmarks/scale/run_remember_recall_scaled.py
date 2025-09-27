"""Scaled harness: POST N /remember concurrently, then /recall.

Usage:
    python3 benchmarks/scale/run_remember_recall_scaled.py --count 1000 --out artifacts/benchmarks/rr_1000.json

This runs against SOMABRAIN_HOST_PORT from .env.local or default 9696.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import time


import httpx

ENV_FILE = ".env.local"
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
                    except Exception:
                        pass
    return port or DEFAULT_PORT


API_PORT = read_env_port()


def make_base(host: str | None = None, port: int | None = None) -> str:
    host = host or "127.0.0.1"
    port = int(port or API_PORT)
    return f"http://{host}:{port}"


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


async def post_remember(
    client: httpx.AsyncClient, i: int, sem: asyncio.Semaphore, retries: int = 2
):
    body = make_payload(i)
    attempt = 0
    try:
        while True:
            attempt += 1
            # semaphore acquisition can be cancelled; let CancelledError propagate to outer handler
            async with sem:
                start = time.perf_counter()
                try:
                    r = await client.post(
                        "/remember", json=body, headers=HEADERS, timeout=30.0
                    )
                    elapsed = (time.perf_counter() - start) * 1000.0
                    return {
                        "i": i,
                        "status": r.status_code,
                        "text": (r.text or "")[:200],
                        "ms": elapsed,
                    }
                except asyncio.CancelledError:
                    # preserve elapsed time and return a cancel marker
                    elapsed = (time.perf_counter() - start) * 1000.0
                    return {"i": i, "status": -1, "text": "cancelled", "ms": elapsed}
                except Exception as e:
                    elapsed = (time.perf_counter() - start) * 1000.0
                    if attempt > retries:
                        return {"i": i, "status": 0, "text": repr(e), "ms": elapsed}
                    backoff = 0.1 * attempt
                    await asyncio.sleep(backoff)
    except asyncio.CancelledError:
        # task was cancelled while sleeping or outside semaphore; return a cancel marker
        return {"i": i, "status": -1, "text": "cancelled", "ms": 0.0}


async def run_count(count: int, concurrency: int = 250, base: str | None = None):
    base_url = base or make_base()
    limits = httpx.Limits(
        max_keepalive_connections=concurrency, max_connections=concurrency
    )
    transport = httpx.AsyncHTTPTransport(retries=1)
    async with httpx.AsyncClient(
        base_url=base_url, limits=limits, transport=transport
    ) as client:
        sem = asyncio.Semaphore(concurrency)
        # create tasks explicitly so we can cancel them on interrupt and inspect partial completion
        tasks = [
            asyncio.create_task(post_remember(client, i, sem)) for i in range(count)
        ]
        print(
            f"Posting {count} /remember to {base_url}/remember with concurrency={concurrency} ..."
        )
        start = time.perf_counter()
        try:
            # Collect results; use return_exceptions=True so we can handle partial failures
            results = await asyncio.gather(*tasks, return_exceptions=True)
        except (asyncio.CancelledError, KeyboardInterrupt):
            # Cancel pending tasks and gather partial results
            print(
                "Run interrupted; cancelling outstanding tasks and gathering partial results..."
            )
            for t in tasks:
                try:
                    t.cancel()
                except Exception:
                    pass
            results = await asyncio.gather(*tasks, return_exceptions=True)
        total_ms = (time.perf_counter() - start) * 1000.0
        # Normalize results: some entries may be exceptions; convert to consistent dicts
        norm_results = []
        for idx, r in enumerate(results):
            if isinstance(r, Exception):
                # Task raised; represent as failure
                norm_results.append(
                    {"i": idx, "status": 0, "text": repr(r), "ms": None}
                )
            else:
                norm_results.append(
                    r
                    if isinstance(r, dict)
                    else {"i": idx, "status": 0, "text": str(r), "ms": None}
                )

        statuses = [r.get("status", 0) for r in norm_results]
        times = [r.get("ms") for r in norm_results if r.get("ms") is not None]
        ok = sum(1 for s in statuses if s == 200)
        stats = {
            "count": count,
            "ok": ok,
            "total_time_ms": total_ms,
            "mean_ms": statistics.mean(times) if times else None,
            "median_ms": statistics.median(times) if times else None,
            "p95_ms": statistics.quantiles(times, n=100)[94] if times else None,
        }
        print(json.dumps(stats, indent=2))

        print("Waiting 1.0s for async persistence...")
        await asyncio.sleep(1.0)
        qstart = time.perf_counter()
        try:
            # use await for the POST call and then inspect/await the response methods
            r = await client.post(
                "/recall",
                json={"query": "scale-memory", "top_k": 20},
                headers=HEADERS,
                timeout=30.0,
            )
            recall_time_ms = (time.perf_counter() - qstart) * 1000.0
            recall_status = r.status_code
            recall_json = None
            if recall_status == 200:
                try:
                    recall_json = r.json()
                except Exception:
                    recall_json = {"error": "invalid json response"}
            else:
                recall_text = r.text
                recall_json = {"error": recall_text}
        except Exception as e:
            recall_time_ms = (time.perf_counter() - qstart) * 1000.0
            recall_status = 0
            recall_json = {"error": repr(e)}

        return {
            "write_stats": stats,
            "recall_status": recall_status,
            "recall": recall_json,
            "recall_time_ms": recall_time_ms,
        }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--count", type=int, default=100)
    p.add_argument("--concurrency", type=int, default=250)
    p.add_argument(
        "--host",
        type=str,
        default=None,
        help="Host for Somabrain API (default 127.0.0.1)",
    )
    p.add_argument(
        "--port",
        type=int,
        default=None,
        help="Port for Somabrain API (overrides .env.local)",
    )
    p.add_argument("--out", type=str, default="artifacts/benchmarks/rr.json")
    args = p.parse_args()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    base = make_base(args.host, args.port)
    res = asyncio.run(run_count(args.count, concurrency=args.concurrency, base=base))
    with open(args.out, "w") as fh:
        json.dump(res, fh, indent=2)
    print("Saved results to", args.out)
