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
    raise SystemExit("replay_outbox.py is removed; JSONL outbox not supported.")

    # Unreachable, kept to satisfy function signature
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--lines", type=int, default=200)
    p.add_argument("--start", type=int, default=0)
    args = p.parse_args()
    sys.exit(replay(lines=args.lines, start=args.start))
