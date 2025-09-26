#!/usr/bin/env python3
from __future__ import annotations

import argparse

from somabrain_client import SomaBrainClient


def main() -> None:
    parser = argparse.ArgumentParser(description="SomaBrain CLI")
    parser.add_argument("query", help="Query text to evaluate")
    parser.add_argument("--session", default="cli-session", help="Session identifier")
    parser.add_argument("--base-url", default="http://localhost:9696/context", help="Base URL")
    parser.add_argument("--token", help="Bearer token")
    args = parser.parse_args()

    client = SomaBrainClient(base_url=args.base_url, api_token=args.token)
    evaluation = client.evaluate(session_id=args.session, query=args.query)
    print("Prompt:\n", evaluation["prompt"])


if __name__ == "__main__":  # pragma: no cover
    main()
