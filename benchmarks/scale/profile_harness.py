"""
Profiling Harness for SomaBrain (S9)
------------------------------------
Profiles CPU and memory usage for any benchmark or API endpoint under load.
Outputs bottleneck analysis and optimization suggestions.
"""

import cProfile
import pstats
import io
import tracemalloc
import time
import importlib

BENCHMARK_MODULE = "benchmarks.plan_bench"
BENCHMARK_FUNC = "run"
BENCHMARK_ARGS: dict = {}


def profile_benchmark():
    print(f"Profiling {BENCHMARK_MODULE}.{BENCHMARK_FUNC}...")
    mod = importlib.import_module(BENCHMARK_MODULE)
    func = getattr(mod, BENCHMARK_FUNC)
    pr = cProfile.Profile()
    tracemalloc.start()
    pr.enable()
    t0 = time.time()
    func(**BENCHMARK_ARGS)
    t1 = time.time()
    pr.disable()
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats("cumulative")
    ps.print_stats(20)
    print(f"--- CPU Profile (top 20 cumulative) ---\n{s.getvalue()}")
    print(
        f"--- Memory usage: current={current / 1e6:.2f}MB, peak={peak / 1e6:.2f}MB ---"
    )
    print(f"--- Wall time: {t1 - t0:.2f}s ---")


if __name__ == "__main__":
    profile_benchmark()
