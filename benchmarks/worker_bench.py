"""Worker-side synthetic RAG pipeline benchmark.

Usage:
  python benchmarks/worker_bench.py --iterations 100

This simulates calling internal retriever stubs and the fusion code paths without network IO.
"""

import argparse
import time

from somabrain.schemas import RAGRequest
from somabrain.services.rag_pipeline import run_rag_pipeline
import asyncio


async def _run_async(iterations: int):
    req = RAGRequest(query="benchmark test", top_k=10)

    # ctx-like stub used by the pipeline
    class Ctx:
        namespace = "bench"
        tenant_id = "bench"

    t0 = time.perf_counter()
    for i in range(iterations):
        await run_rag_pipeline(
            req, ctx=Ctx(), cfg=None, universe=None, trace_id=f"b{i}"
        )
    t1 = time.perf_counter()
    print(
        f"Simulated {iterations} pipelines in {t1 - t0:.3f}s ({iterations / (t1 - t0):.1f} ops/s)"
    )


def run(iterations: int):
    asyncio.run(_run_async(iterations))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=100)
    args = parser.parse_args()
    run(args.iterations)
