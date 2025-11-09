#!/usr/bin/env python3
"""Capture golden memory samples from the live SomaBrain memory endpoint.

This script records real responses (no mocks) and emits JSON-lines files under
`tests/data/golden/`. Use it when refreshing canonical datasets.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import httpx

DEFAULT_ENDPOINT = "http://localhost:9696"


def capture_memories(endpoint: str, tenant: str, output: Path) -> None:
    client = httpx.Client(base_url=endpoint, timeout=30.0)
    payload = {
        "task": "capture-golden",
        "content": "golden truth sample",
        "importance": 0.9,
    }
    resp = client.post("/remember", json=payload, headers={"X-Tenant-ID": tenant})
    resp.raise_for_status()
    recall = client.post(
        "/recall", json={"query": payload["task"]}, headers={"X-Tenant-ID": tenant}
    )
    recall.raise_for_status()
    data = recall.json()
    entry = {
        "tenant_id": tenant,
        "task": payload["task"],
        "content": payload["content"],
        "importance": payload["importance"],
        "results": data.get("results", []),
    }
    output.write_text(json.dumps(entry) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Capture golden memory samples")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--tenant", default="demo")
    parser.add_argument("--output", default="tests/data/golden/memories.jsonl")
    args = parser.parse_args(argv)
    capture_memories(args.endpoint, args.tenant, Path(args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
