"""Replay outbox.jsonl entries through Somabrain /remember endpoint.

Usage: python scripts/replay_outbox.py [--lines N] [--start S]

Defaults: N=200, start=0

This script is intentionally conservative: it only posts entries whose op == 'remember'
and sends the inner `payload.payload` object as the `payload` field expected by
Somabrain's /remember API.

It prints a short summary and exits. It does not delete the outbox file.
"""

import sys
import json
import argparse
from pathlib import Path

import httpx

OUTBOX = Path("./data/somabrain/outbox.jsonl")
SOMABRAIN_URL = "http://localhost:9696"


def replay(lines: int = 200, start: int = 0):
    if not OUTBOX.exists():
        print(f"Outbox file not found: {OUTBOX}")
        return 1

    total = 0
    success = 0
    failed = 0
    client = httpx.Client(timeout=15.0)

    with OUTBOX.open("r", encoding="utf-8") as fh:
        # skip to start
        for _ in range(start):
            line = fh.readline()
            if not line:
                break
        # iterate up to lines
        for i in range(lines):
            line = fh.readline()
            if not line:
                break
            total += 1
            try:
                obj = json.loads(line)
            except Exception as e:
                print(f"Line parse error at #{start+i}: {e}")
                failed += 1
                continue
            op = obj.get("op")
            if op != "remember":
                # skip non-remember ops
                continue
            payload_wrapper = obj.get("payload") or {}
            inner = payload_wrapper.get("payload")
            if inner is None:
                print(f"Missing inner payload at line #{start+i}")
                failed += 1
                continue
            body = {"payload": inner}
            # include coord if present and is an x,y,z string
            coord = payload_wrapper.get("coord") or payload_wrapper.get("coord_key")
            if isinstance(coord, str) and "," in coord:
                body["coord"] = coord
            try:
                r = client.post(SOMABRAIN_URL + "/remember", json=body)
                if r.status_code == 200:
                    success += 1
                else:
                    print(f"POST /remember -> {r.status_code}: {r.text[:200]}")
                    failed += 1
            except Exception as e:
                print(f"HTTP error posting line #{start+i}: {e}")
                failed += 1
    print("--- replay summary ---")
    print(f"requested lines: {lines}, read/processed: {total}")
    print(f"success: {success}, failed: {failed}")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--lines", type=int, default=200)
    p.add_argument("--start", type=int, default=0)
    args = p.parse_args()
    sys.exit(replay(lines=args.lines, start=args.start))
