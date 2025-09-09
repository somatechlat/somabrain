#!/usr/bin/env python3
"""Micro-benchmarks for HRR primitives and optional API latency tests.

Writes CSV results to repo root: hrr_benchmark_results.csv and api_benchmark_results.csv
"""
import csv
import platform
import statistics
import sys
import time

import numpy as np

from somabrain.quantum import HRRConfig, QuantumLayer

try:
    import requests
except Exception:
    requests = None


def make_vec(dim, dtype=np.float32):
    v = np.random.randn(dim).astype(dtype)
    n = np.linalg.norm(v)
    if n == 0:
        return v
    return v / n


def bench_hrr(dim, dtype_str, iters):
    dtype = np.dtype(dtype_str)
    cfg = HRRConfig(dim=dim, seed=42)
    q = QuantumLayer(cfg)

    a = make_vec(dim, dtype=dtype)
    b = make_vec(dim, dtype=dtype)

    # warmup
    for _ in range(5):
        c = q.bind(a, b)
        _ = q.unbind(c, b)

    times = {"bind": [], "unbind": [], "permute": [], "cleanup": []}

    # prepare anchors for cleanup
    anchors = {f"k{i}": make_vec(dim, dtype=dtype) for i in range(100)}

    for i in range(iters):
        t0 = time.perf_counter()
        c = q.bind(a, b)
        t1 = time.perf_counter()
        times["bind"].append(t1 - t0)

        t0 = time.perf_counter()
        _a_est = q.unbind(c, b)
        t1 = time.perf_counter()
        times["unbind"].append(t1 - t0)

        t0 = time.perf_counter()
        _p = q.permute(a)
        t1 = time.perf_counter()
        times["permute"].append(t1 - t0)

        # cleanup: simulate superposition of k=4
        s = a + b + make_vec(dim, dtype=dtype) + make_vec(dim, dtype=dtype)
        s = s / max(np.linalg.norm(s), 1e-12)
        t0 = time.perf_counter()
        _cand = q.cleanup(s, anchors)
        t1 = time.perf_counter()
        times["cleanup"].append(t1 - t0)

    summary = {}
    for op, lst in times.items():
        summary[op] = {
            "mean_s": statistics.mean(lst),
            "median_s": statistics.median(lst),
            "stdev_s": statistics.stdev(lst) if len(lst) > 1 else 0.0,
            "n": len(lst),
        }

    return summary


def run_all():
    results = []

    dims = [256, 512, 1024]
    dtype_map = ["float32", "float64"]
    for dim in dims:
        for dtype in dtype_map:
            if dim <= 256:
                iters = 200
            elif dim <= 512:
                iters = 100
            else:
                iters = 50

            print(f"Benchmarking dim={dim} dtype={dtype} iters={iters}")
            sys.stdout.flush()
            s = bench_hrr(dim, dtype, iters)
            for op, stats in s.items():
                results.append(
                    {
                        "dim": dim,
                        "dtype": dtype,
                        "op": op,
                        "mean_s": stats["mean_s"],
                        "median_s": stats["median_s"],
                        "stdev_s": stats["stdev_s"],
                        "n": stats["n"],
                    }
                )

    # write CSV
    out = "hrr_benchmark_results.csv"
    with open(out, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["dim", "dtype", "op", "mean_s", "median_s", "stdev_s", "n"]
        )
        writer.writeheader()
        for row in results:
            writer.writerow(row)

    print("\nHRR benchmark completed. Results written to", out)

    # Optional API benchmark
    api_results = []
    if requests is None:
        print("requests not installed; skipping API benchmark")
    else:
        base = "http://127.0.0.1:9696"
        # try /health
        try:
            r = requests.get(base + "/health", timeout=1.0)
            print("Server health status", r.status_code)
            # run small remember/recall benchmark
            for ep in ["remember", "recall"]:
                latencies = []
                n = 30
                for i in range(n):
                    try:
                        if ep == "remember":
                            payload = {
                                "coord": "1,2,3",
                                "payload": {"task": "bench", "importance": 1},
                            }
                            t0 = time.perf_counter()
                            _ = requests.post(
                                base + "/remember", json=payload, timeout=2.0
                            )
                            t1 = time.perf_counter()
                        else:
                            payload = {"query": "bench", "top_k": 3}
                            t0 = time.perf_counter()
                            _ = requests.post(
                                base + "/recall", json=payload, timeout=2.0
                            )
                            t1 = time.perf_counter()
                        latencies.append(t1 - t0)
                    except Exception:
                        latencies.append(None)

                good = [lat for lat in latencies if lat is not None]
                api_results.append(
                    {
                        "endpoint": ep,
                        "count": n,
                        "success": len(good),
                        "mean_s": statistics.mean(good) if good else None,
                        "median_s": statistics.median(good) if good else None,
                    }
                )
        except Exception as e:
            print("Server not reachable at", base, "skipping API benchmarks:", e)

    if api_results:
        out2 = "api_benchmark_results.csv"
        with open(out2, "w", newline="") as f:
            writer = csv.DictWriter(
                f, fieldnames=["endpoint", "count", "success", "mean_s", "median_s"]
            )
            writer.writeheader()
            for r in api_results:
                writer.writerow(r)
        print("API benchmark results written to", out2)


if __name__ == "__main__":
    print("Python:", platform.python_version())
    print("Platform:", platform.platform())
    run_all()
