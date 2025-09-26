"""
Load, Soak, and Spike Test Harness for SomaBrain (S9)
-----------------------------------------------------
Simulates different traffic patterns to stress the system and record bottlenecks.
"""
import time
import threading
import statistics
from fastapi.testclient import TestClient
from somabrain.app import app

ENDPOINT = "/recall"
REQUEST_BODY = {"query": "benchmark", "top_k": 1}
HEADERS = {}

results = []
errors = 0
lock = threading.Lock()

def run_pattern(pattern, duration_s, concurrency, rps=None):
    global errors
    client = TestClient(app)
    stop_time = time.time() + duration_s
    def worker():
        while time.time() < stop_time:
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
            if rps:
                sleep_time = max(0, 1.0/rps - (time.time()-t0))
                if sleep_time > 0:
                    time.sleep(sleep_time)
    threads = [threading.Thread(target=worker) for _ in range(concurrency)]
    for th in threads:
        th.start()
    for th in threads:
        th.join()

def main():
    print("--- Load Test: Steady RPS ---")
    run_pattern("load", duration_s=60, concurrency=16, rps=50)
    print(f"Total requests: {len(results)} | Errors: {errors}")
    if results:
        print(f"p50: {statistics.median(results):.4f}s | p95: {statistics.quantiles(results, n=100)[94]:.4f}s | p99: {statistics.quantiles(results, n=100)[98]:.4f}s")
    results.clear()
    print("--- Soak Test: Long Duration ---")
    run_pattern("soak", duration_s=600, concurrency=8, rps=10)
    print(f"Total requests: {len(results)} | Errors: {errors}")
    if results:
        print(f"p50: {statistics.median(results):.4f}s | p95: {statistics.quantiles(results, n=100)[94]:.4f}s | p99: {statistics.quantiles(results, n=100)[98]:.4f}s")
    results.clear()
    print("--- Spike Test: Sudden Burst ---")
    run_pattern("spike", duration_s=10, concurrency=64, rps=None)
    print(f"Total requests: {len(results)} | Errors: {errors}")
    if results:
        print(f"p50: {statistics.median(results):.4f}s | p95: {statistics.quantiles(results, n=100)[94]:.4f}s | p99: {statistics.quantiles(results, n=100)[98]:.4f}s")

if __name__ == "__main__":
    main()
