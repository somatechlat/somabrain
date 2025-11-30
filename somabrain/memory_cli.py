import argparse
import json
from urllib.parse import urljoin
import requests  # type: ignore
from somabrain.infrastructure import get_api_base_url, require
from common.logging import logger

# somabrain/memory_cli.py
"""
Simple command‑line client for the SomaBrain memory service.

Usage examples:
    $ python -m somabrain.memory_cli remember "My favorite color is blue."
    $ python -m somabrain.memory_cli recall "What is my favorite color?"
    $ python -m somabrain.memory_cli get <key>
"""




# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
BASE_URL = require(
    get_api_base_url(),
    message="SOMABRAIN_API_URL is not configured; update your environment (.env).", )
HEADERS = {"Content-Type": "application/json"}


def _post(endpoint: str, payload: dict):
    url = urljoin(BASE_URL + "/", endpoint.lstrip("/"))
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        resp = requests.post(url, headers=HEADERS, data=json.dumps(payload))
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.exception("Exception caught: %s", e)
        raise


def _get(endpoint: str):
    url = urljoin(BASE_URL + "/", endpoint.lstrip("/"))
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        resp = requests.get(url, headers=HEADERS)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.exception("Exception caught: %s", e)
        raise


# ----------------------------------------------------------------------
# CLI command implementations
# ----------------------------------------------------------------------
def cmd_remember(args):
    payload = {"payload": {"text": args.text}}
    result = _post("/remember", payload)
    print(json.dumps(result, indent=2))


def cmd_recall(args):
    payload = {"query": args.query}
    result = _post("/recall", payload)
    print(json.dumps(result, indent=2))


def cmd_get(args):
    result = _get(f"/memory/{args.key}")
    print(json.dumps(result, indent=2))


def cmd_link(args):
    payload = {"from_key": args.from_key, "to_key": args.to_key}
    result = _post("/link", payload)
    print(json.dumps(result, indent=2))


# ----------------------------------------------------------------------
# Argument parser
# ----------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="memory_cli",
        description="Interact with SomaBrain memory service from the command line.", )
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

    p_link = sub.add_parser("link", help="Create a link between two memories.")
    p_link.add_argument("from_key", help="Source memory key.")
    p_link.add_argument("to_key", help="Target memory key.")
    p_link.set_defaults(func=cmd_link)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
