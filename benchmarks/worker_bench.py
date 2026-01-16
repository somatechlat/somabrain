"""Worker-side synthetic retrieval pipeline benchmark.

Usage:
    python benchmarks/worker_bench.py --iterations 100

Notes:
- This is a synthetic micro-benchmark that exercises lightweight in-process retrieval
    and fusion code paths only. It does NOT perform any network IO or call live services
    (API, Kafka, Postgres). Therefore it is NOT an end-to-end benchmark and should
    not be used to substantiate production latency/throughput claims. Use
    `benchmarks/recall_latency_bench.py`, `benchmarks/recall_live_bench.py`, or
    `benchmarks/http_bench.py` against a running stack for live measurements.
"""

import argparse
import time

from somabrain.schemas import RetrievalRequest
from somabrain.services.retrieval_pipeline import run_retrieval_pipeline
import asyncio


async def _run_async(iterations: int):
    """Execute run async.

    Args:
        iterations: The iterations.
    """

    req = RetrievalRequest(query="benchmark test", top_k=10)

    # Minimal context object used by the pipeline
    class Ctx:
        """Ctx class implementation."""

        namespace = "bench"
        tenant_id = "bench"

    t0 = time.perf_counter()
    for i in range(iterations):
        await run_retrieval_pipeline(req, ctx=Ctx(), cfg=None, universe=None, trace_id=f"b{i}")
    t1 = time.perf_counter()
    print(
        f"Simulated {iterations} pipelines in {t1 - t0:.3f}s ({iterations / (t1 - t0):.1f} ops/s)"
    )


def run(iterations: int):
    """Execute run.

    Args:
        iterations: The iterations.
    """

    asyncio.run(_run_async(iterations))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=100)
    args = parser.parse_args()
    run(args.iterations)
