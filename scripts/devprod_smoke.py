#!/usr/bin/env python3
"""
Dev-Prod Smoke Test

Verifies live learning behavior against a running Somabrain API by:
1) POST /memory/remember to write a memory
2) POST /memory/recall to retrieve it

Usage:
  SOMA_API_URL=http://127.0.0.1:9696 python scripts/devprod_smoke.py
  python scripts/devprod_smoke.py --url http://127.0.0.1:9696 --universe real

Exit codes:
  0 on success, non-zero on failure
"""

from __future__ import annotations

import argparse
from somabrain.infrastructure import get_api_base_url
import sys
import time
from typing import Any, Dict

import requests


def post_json(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    r = requests.post(url, json=payload, timeout=10)
    r.raise_for_status()
    try:
        return r.json()
    except Exception:
        raise RuntimeError(f"Non-JSON response from {url}: {r.text[:200]}")


def run_smoke(base_url: str, universe: str | None = None) -> None:
    remember_url = f"{base_url}/memory/remember"
    recall_url = f"{base_url}/memory/recall"
    key_text = f"devprod smoke task {int(time.time()*1000)}"
    payload = {
        "coord": None,
        "payload": {
            "task": key_text,
            "importance": 1,
            "memory_type": "episodic",
            **({"universe": universe} if universe else {}),
        },
    }

    # 1) remember
    rj = post_json(remember_url, payload)
    if not (rj.get("ok") and rj.get("success")):
        raise SystemExit(f"/memory/remember failed: {rj}")

    # Small delay to allow WM admission and caches to settle in dev environments
    time.sleep(0.4)
    # 2) recall (read-your-writes should succeed)
    body = {
        "query": key_text,
        "top_k": 5,
        **({"universe": universe} if universe else {}),
    }
    r2 = post_json(recall_url, body)
    candidates = []
    for key in ("memory", "wm"):
        seq = r2.get(key)
        if isinstance(seq, list):
            candidates.extend(seq)

    text_lower = key_text.lower()
    found = False
    for p in candidates:
        if isinstance(p, dict):
            t = str(p.get("task") or p.get("fact") or p.get("text") or "").lower()
            if t and (text_lower in t or t in text_lower):
                found = True
                break
    if not found:
        raise SystemExit(
            f"/memory/recall did not include the freshly stored memory. Response: {r2}"
        )

    print("OK: memory/remember and memory/recall read-your-writes verified.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=get_api_base_url())
    from django.conf import settings

    ap.add_argument("--universe", default=settings.universe)
    args = ap.parse_args()
    try:
        run_smoke(args.url.rstrip("/"), args.universe)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(2)

    sys.exit(0)


if __name__ == "__main__":
    main()
