"""Simple HTTP benchmark harness using httpx.

Usage:
    python benchmarks/http_bench.py --url http://localhost:9696/recall --concurrency 8 --requests 200

This sends POST requests with a simple RetrievalRequest body and prints latency percentiles.
"""

import argparse
from django.conf import settings
import asyncio
import time
from statistics import mean, median

import httpx

DEFAULT_BODY = {
    "query": "What is the capital of France?",
    "top_k": 5,
    "retrievers": ["vector", "wm"],
}


async def worker(client: httpx.AsyncClient, url: str, q: asyncio.Queue, results: list):
    """Execute worker.

    Args:
        client: The client.
        url: The url.
        q: The q.
        results: The results.
    """

    while True:
        try:
            _ = q.get_nowait()
        except Exception:
            break
        t0 = time.perf_counter()
        try:
            r = await client.post(url, json=DEFAULT_BODY, timeout=30.0)
            latency = time.perf_counter() - t0
            results.append((r.status_code, latency))
        except Exception:
            latency = time.perf_counter() - t0
            results.append((None, latency))


async def run(url: str, concurrency: int, total: int):
    """Execute run.

    Args:
        url: The url.
        concurrency: The concurrency.
        total: The total.
    """

    q = asyncio.Queue()
    for i in range(total):
        q.put_nowait(i)
    results = []
    async with httpx.AsyncClient() as client:
        tasks = [
            asyncio.create_task(worker(client, url, q, results))
            for _ in range(concurrency)
        ]
        await asyncio.gather(*tasks)
    codes = [r for r, _ in results if r is not None]
    latencies = [lat for _, lat in results]
    print(f"sent: {len(results)}, success: {len([c for c in codes if c and c < 400])}")
    if latencies:
        print(f"mean: {mean(latencies):.4f}s, median: {median(latencies):.4f}s")
        lat_sorted = sorted(latencies)
        p50 = lat_sorted[int(0.5 * len(lat_sorted))]
        p90 = lat_sorted[int(0.9 * len(lat_sorted))]
        p99 = (
            lat_sorted[int(0.99 * len(lat_sorted))]
            if len(lat_sorted) > 100
            else lat_sorted[-1]
        )
        print(f"p50: {p50:.4f}s p90: {p90:.4f}s p99: {p99:.4f}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=f"{settings.api_url}/memory/recall")
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--requests", type=int, default=100)
    args = parser.parse_args()
    asyncio.run(run(args.url, args.concurrency, args.requests))
