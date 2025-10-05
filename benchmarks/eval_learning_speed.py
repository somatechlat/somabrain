"""Evaluate learning speed: measures precision@1 after incremental seeding.

Prerequisite: run `scripts/seed_bench_data.py --count N` or seed using the same API.
This script expects the first seed manifest in `artifacts/benchmarks/` and will
query `/rag/retrieve` for a set of evaluation queries derived from the seeded items.
"""

import glob
import json
import os
from datetime import datetime

import httpx


def load_manifest():
    paths = sorted(glob.glob("artifacts/benchmarks/seed_manifest_*.json"))
    if not paths:
        raise RuntimeError("No seed manifest found in artifacts/benchmarks/")
    with open(paths[-1]) as f:
        return json.load(f)


def eval_precision_at_1(base_url: str, items):
    client = httpx.Client(timeout=20.0)
    url = base_url.rstrip("/") + "/rag/retrieve"
    correct = 0
    total = 0
    for it in items:
        query = f"Who wrote Book{it['i']}?"
        body = {"query": query, "top_k": 5}
        try:
            r = client.post(url, json=body)
            total += 1
            if r.status_code == 200:
                j = r.json()
                cands = j.get("candidates", [])
                # check if any candidate payload contains the author string
                expected = f"Author{it['i']}"
                found = any(expected in str(c.get("payload", {})) for c in cands[:1])
                if found:
                    correct += 1
        except Exception as e:
            print("error", e)
    return correct, total


def main():
    manifest = load_manifest()
    base_url = manifest.get("base_url", "http://localhost:9696")
    items = manifest.get("items", [])
    checkpoints = [10, 50, 100, 500, 1000, len(items)]
    results = []
    for ck in checkpoints:
        subset = items[: min(ck, len(items))]
        correct, total = eval_precision_at_1(base_url, subset)
        results.append({"n": len(subset), "precision_at_1": correct / max(1, total)})
        print(f"n={len(subset)} precision@1={results[-1]['precision_at_1']:.3f}")
    os.makedirs("artifacts/benchmarks", exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out = {"run_at": ts, "base_url": base_url, "results": results}
    fname = f"artifacts/benchmarks/learning_speed_{ts}.json"
    with open(fname, "w") as f:
        json.dump(out, f, indent=2)
    print(f"Wrote {fname}")


if __name__ == "__main__":
    main()
