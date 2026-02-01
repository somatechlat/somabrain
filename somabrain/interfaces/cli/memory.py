# somabrain/memory_cli.py
"""
Simple command‑line client for the SomaBrain memory service.

Usage examples:
    $ python -m somabrain.interfaces.cli.memory remember "My favorite color is blue."
    $ python -m somabrain.interfaces.cli.memory recall "What is my favorite color?"
    $ python -m somabrain.interfaces.cli.memory get <key>
"""

import argparse
import json
import sys
from urllib.parse import urljoin

import requests

from somabrain.core.infrastructure_defs import get_api_base_url, require

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
BASE_URL = require(
    get_api_base_url(),
    message="SOMABRAIN_API_URL is not configured; update your environment (.env).",
)
HEADERS = {"Content-Type": "application/json"}


def _post(endpoint: str, payload: dict):
    """Execute post.

    Args:
        endpoint: The endpoint.
        payload: The payload.
    """

    url = urljoin(BASE_URL + "/", endpoint.lstrip("/"))
    try:
        resp = requests.post(url, headers=HEADERS, data=json.dumps(payload))
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        sys.stderr.write(f"❌ POST {url} failed: {e}\n")
        sys.exit(1)


def _get(endpoint: str):
    """Execute get.

    Args:
        endpoint: The endpoint.
    """

    url = urljoin(BASE_URL + "/", endpoint.lstrip("/"))
    try:
        resp = requests.get(url, headers=HEADERS)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        sys.stderr.write(f"❌ GET {url} failed: {e}\n")
        sys.exit(1)


# ----------------------------------------------------------------------
# CLI command implementations
# ----------------------------------------------------------------------
def cmd_remember(args):
    """Execute cmd remember.

    Args:
        args: The args.
    """

    payload = {"payload": {"text": args.text}}
    result = _post("/memory/remember", payload)
    print(json.dumps(result, indent=2))


def cmd_recall(args):
    """Execute cmd recall.

    Args:
        args: The args.
    """

    payload = {"query": args.query}
    result = _post("/memory/recall", payload)
    print(json.dumps(result, indent=2))


def cmd_get(args):
    """Execute cmd get.

    Args:
        args: The args.
    """

    result = _get(f"/memory/{args.key}")
    print(json.dumps(result, indent=2))


# ----------------------------------------------------------------------
# Argument parser
# ----------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    """Execute build parser."""

    parser = argparse.ArgumentParser(
        prog="memory_cli",
        description="Interact with SomaBrain memory service from the command line.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_rem = sub.add_parser("remember", help="Store a free‑form text memory.")
    p_rem.add_argument("text", help="The text to remember.")
    p_rem.set_defaults(func=cmd_remember)

    p_rec = sub.add_parser("recall", help="Recall memories based on a query.")
    p_rec.add_argument("query", help="Natural‑language query.")
    p_rec.set_defaults(func=cmd_recall)

    p_get = sub.add_parser("get", help="Fetch a memory by its key.")
    p_get.add_argument("key", help="Memory key (as returned by /remember).")
    p_get.set_defaults(func=cmd_get)

    return parser


def main():
    """Execute main."""

    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
