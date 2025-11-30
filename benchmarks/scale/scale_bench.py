"""
Scale Benchmark Suite for SomaBrain (S9)
----------------------------------------
Simulates high request volume to API endpoints, captures SLO metrics (latency, error rate), and outputs results for analysis.
"""

import time
import threading
import statistics
from fastapi.testclient import TestClient
from somabrain.app import app

TARGET_REQUESTS = 1000000  # 1M requests
CONCURRENCY = 32  # Number of concurrent threads
ENDPOINT = "/recall"  # Example endpoint to stress
REQUEST_BODY = {"query": "benchmark", "top_k": 1}
HEADERS = {}

results = []
errors = 0
lock = threading.Lock()


def worker(n):
    global errors
    client = TestClient(app)
    for _ in range(n):
        t0 = time.time()
        try:
            r = client.post(ENDPOINT, json=REQUEST_BODY, headers=HEADERS)
            latency = time.time() - t0
            with lock:
                results.append(latency)
            if r.status_code != 200:
                with lock:
                    errors += 1
        except Exception:
            with lock:
                errors += 1


def main():
    per_thread = TARGET_REQUESTS // CONCURRENCY
    threads = [
        threading.Thread(target=worker, args=(per_thread,)) for _ in range(CONCURRENCY)
    ]
    t_start = time.time()
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    t_total = time.time() - t_start
    print(f"Total requests: {len(results)}")
    print(f"Errors: {errors}")
    print(f"Total time: {t_total:.2f}s")
    if results:
        print(f"p50 latency: {statistics.median(results):.4f}s")
        print(f"p95 latency: {statistics.quantiles(results, n=100)[94]:.4f}s")
        print(f"p99 latency: {statistics.quantiles(results, n=100)[98]:.4f}s")
        print(f"Throughput: {len(results) / t_total:.2f} req/s")


if __name__ == "__main__":
    main()
