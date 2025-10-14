# Benchmark for measuring link operation latency and throughput in the in-process memory backend.

"""
Benchmark script to evaluate the performance of creating edges (links) in the
MemoryClient graph. It generates a set of random coordinates, links them in a
pairwise fashion, and reports average latency per link and total throughput.

Usage:
    $ ./.venv/bin/python benchmarks/benchmark_link_latency.py [NUM_LINKS]

If NUM_LINKS is omitted, defaults to 10,000 links.
"""

import copy
import random
import time
from typing import List, Tuple

from somabrain.config import get_config
from somabrain.memory_pool import MultiTenantMemory


def _random_coord() -> Tuple[float, float, float]:
    """Generate a deterministic random coordinate in the range [-1, 1]."""
    return (
        random.uniform(-1.0, 1.0),
        random.uniform(-1.0, 1.0),
        random.uniform(-1.0, 1.0),
    )


def run_benchmark(num_links: int = 10_000) -> None:
    cfg = copy.deepcopy(get_config())
    # Memory modes removed. Ensure HTTP endpoint configured for the memory service
    cfg.http.endpoint = cfg.http.endpoint or "http://localhost:9595"
    pool = MultiTenantMemory(cfg)
    namespace = "benchmark:link_latency"
    client = pool.for_namespace(namespace)

    # Pre-generate coordinates to avoid timing their creation.
    coords: List[Tuple[float, float, float]] = [
        _random_coord() for _ in range(num_links * 2)
    ]
    from_coords = coords[0::2]
    to_coords = coords[1::2]

    start = time.perf_counter()
    for f, t in zip(from_coords, to_coords):
        client.link(f, t, link_type="benchmark", weight=1.0)
    elapsed = time.perf_counter() - start

    avg_latency_ms = (elapsed / num_links) * 1_000
    throughput = num_links / elapsed
    print(f"Linked {num_links:,} edges in {elapsed:.3f}s")
    print(f"Average latency per link: {avg_latency_ms:.3f} ms")
    print(f"Throughput: {throughput:,.0f} links/sec")


if __name__ == "__main__":
    import sys

    try:
        n = int(sys.argv[1]) if len(sys.argv) > 1 else 10_000
    except ValueError:
        n = 10_000
    run_benchmark(n)
