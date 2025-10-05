"""Exercise the live Somabrain persona API and SomaMemory recall endpoint.

The original version of this script emitted synthetic transcripts for mocked
tests.  It now performs a real round-trip against the deployed stack, mirroring
``tests/test_synthetic_memory_recall.py`` but in a CLI-friendly form.

Example
-------
    $ python scripts/generate_synthetic_memory.py \
        --api-base http://localhost:9696 \
        --memory-base http://localhost:9595

The command validates connectivity, writes a temporary persona, confirms recall
through SomaMemory, and deletes the persona on success.
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from typing import Sequence

import requests

from somabrain.testing.synthetic_memory import (
    require_http_service,
    require_tcp_endpoint,
)


def put_persona(api_base: str, persona_id: str, payload: dict) -> requests.Response:
    resp = requests.put(f"{api_base}/persona/{persona_id}", json=payload, timeout=10)
    resp.raise_for_status()
    return resp


def get_persona(api_base: str, persona_id: str) -> dict:
    resp = requests.get(f"{api_base}/persona/{persona_id}", timeout=10)
    resp.raise_for_status()
    return resp.json()


def recall_persona(memory_base: str, persona_id: str) -> list[dict]:
    resp = requests.post(
        f"{memory_base}/recall", json={"query": persona_id, "top_k": 50}, timeout=10
    )
    resp.raise_for_status()
    return resp.json()


def delete_persona(api_base: str, persona_id: str) -> None:
    resp = requests.delete(f"{api_base}/persona/{persona_id}", timeout=10)
    resp.raise_for_status()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--api-base",
        default=os.getenv("SOMA_API_URL", "http://localhost:9696"),
        help="Base URL for the Somabrain API (default: %(default)s)",
    )
    parser.add_argument(
        "--memory-base",
        default=os.getenv("SOMABRAIN_MEMORY_HTTP_ENDPOINT", "http://localhost:9595"),
        help="Base URL for the SomaMemory HTTP service (default: %(default)s)",
    )
    parser.add_argument(
        "--redis-host",
        default=os.getenv("REDIS_HOST", "127.0.0.1"),
        help="Redis host used by the stack (default: %(default)s)",
    )
    parser.add_argument(
        "--redis-port",
        type=int,
        default=int(os.getenv("REDIS_PORT", "6379")),
        help="Redis port used by the stack (default: %(default)s)",
    )
    parser.add_argument(
        "--display-name",
        default="Integration Test Persona",
        help="Display name to store on the persona (default: %(default)s)",
    )
    parser.add_argument(
        "--persona-id",
        help="Optional explicit persona identifier (default: generated UUID)",
    )
    args = parser.parse_args(argv)

    persona_id = args.persona_id or f"cli-{uuid.uuid4().hex[:12]}"
    payload = {
        "display_name": args.display_name,
        "properties": {
            "origin": "integration-cli",
            "persona_id": persona_id,
        },
    }

    require_tcp_endpoint(args.redis_host, args.redis_port)
    require_http_service(args.api_base, "/demo")
    require_http_service(args.memory_base)

    print(
        f"✔ Connectivity verified (Redis {args.redis_host}:{args.redis_port})",
        file=sys.stderr,
    )
    print(f"✔ API reachable at {args.api_base}", file=sys.stderr)
    print(f"✔ Memory service reachable at {args.memory_base}", file=sys.stderr)

    try:
        put_persona(args.api_base, persona_id, payload)
        print(f"✔ Persona stored: {persona_id}", file=sys.stderr)

        stored = get_persona(args.api_base, persona_id)
        print(
            f"✔ Persona retrieved with display_name={stored['display_name']}",
            file=sys.stderr,
        )

        memories = recall_persona(args.memory_base, persona_id)
        if any(mem.get("id") == persona_id for mem in memories):
            print(
                f"✔ Persona recalled from SomaMemory ({len(memories)} memories total)",
                file=sys.stderr,
            )
        else:
            print("✖ Persona not present in recall results", file=sys.stderr)
            return 1

        print(persona_id)
        return 0
    finally:
        try:
            delete_persona(args.api_base, persona_id)
            print(f"✔ Persona deleted: {persona_id}", file=sys.stderr)
        except Exception as exc:  # pragma: no cover - cleanup best-effort
            print(f"⚠ Failed to delete persona {persona_id}: {exc}", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
