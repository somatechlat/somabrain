"""Seed the memory backend via HTTP /remember for benchmark datasets.

Usage:
  python scripts/seed_bench_data.py --count 1000 --base-url http://localhost:9696

This creates simple "fact" payloads like {"task": "Author of Book{i} is Author{i}"}
and calls the `/remember` API to persist them. The script writes a JSON manifest
to `artifacts/benchmarks/seed_manifest_{timestamp}.json` with the inserted keys.
"""

import argparse
from django.conf import settings
import json
import os
from datetime import datetime

import httpx


def main(count: int, base_url: str, namespace: str | None = None):
    out = []
    client = httpx.Client(timeout=30.0)
    remember_url = base_url.rstrip("/") + "/memory/remember"
    for i in range(count):
        key = f"book:{i}"
        author = f"Author{i}"
        payload = {
            "payload": {
                "task": f"Author of Book{i} is {author}",
                "memory_type": "episodic",
                "who": author,
            }
        }
        if namespace:
            headers = {"X-Universe": namespace}
        else:
            headers = {}
        try:
            r = client.post(remember_url, json=payload, headers=headers)
            if r.status_code >= 400:
                print(f"WARN: seed {i} returned status {r.status_code}: {r.text}")
            out.append({"key": key, "i": i, "status": r.status_code})
        except Exception as e:
            print(f"ERROR: seed {i} exception: {e}")
            out.append({"key": key, "i": i, "status": "error", "error": str(e)})
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    os.makedirs("artifacts/benchmarks", exist_ok=True)
    fname = f"artifacts/benchmarks/seed_manifest_{ts}.json"
    with open(fname, "w") as f:
        json.dump({"base_url": base_url, "count": count, "items": out}, f, indent=2)
    print(f"Wrote manifest to {fname}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--count", type=int, default=1000)
    p.add_argument("--base-url", default=settings.api_url)
    p.add_argument("--namespace", default=None)
    args = p.parse_args()
    main(args.count, args.base_url, args.namespace)
