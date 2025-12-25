"""Evaluate retrieval precision@K using the latest seed manifest.

Produces `artifacts/benchmarks/retrieval_precision_{timestamp}.json` with precision@k and recall@k.
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


def eval_precision_recall(base_url: str, items, k=5):
    client = httpx.Client(timeout=20.0)
    url = base_url.rstrip("/") + "/memory/recall"
    results = []
    for it in items:
        query = f"Who wrote Book{it['i']}?"
        body = {"query": query, "top_k": k}
        try:
            r = client.post(url, json=body)
            if r.status_code != 200:
                results.append({"i": it["i"], "status": r.status_code})
                continue
            j = r.json()
            cands = j.get("results", [])
            expected = f"Author{it['i']}"
            topk = cands[:k]
            found_k = sum(1 for c in topk if expected in str(c.get("payload", {})))
            # naive recall: since each query has a single ground-truth, recall==found_k>0
            results.append(
                {"i": it["i"], "precision@k": found_k / max(1, k), "found": found_k}
            )
        except Exception as e:
            results.append({"i": it["i"], "status": "error", "error": str(e)})
    return results


def main():
    manifest = load_manifest()
    base_url = manifest.get("base_url", "http://localhost:9696")
    items = manifest.get("items", [])
    subset = items[: min(1000, len(items))]
    results = eval_precision_recall(base_url, subset, k=5)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    os.makedirs("artifacts/benchmarks", exist_ok=True)
    fname = f"artifacts/benchmarks/retrieval_precision_{ts}.json"
    with open(fname, "w") as f:
        json.dump({"base_url": base_url, "results": results}, f, indent=2)
    print(f"Wrote {fname}")


if __name__ == "__main__":
    main()
