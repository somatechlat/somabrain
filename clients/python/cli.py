from __future__ import annotations
import argparse
from somabrain_client import SomaBrainClient


def main() -> None:
    """Entry point for the SomaBrain command‑line interface.

    The CLI accepts a query string, optional session identifier, base URL for the
    SomaBrain HTTP API, and an optional bearer token.  It creates a
    :class:`SomaBrainClient`, sends the query for evaluation, and prints the
    returned prompt to stdout.
    """
    parser = argparse.ArgumentParser(description="SomaBrain CLI")
    parser.add_argument("query", help="Query text to evaluate")
    parser.add_argument("--session", default="cli-session", help="Session identifier")
    # Use the centralized default base URL from Settings; append the context path.
    from common.config.settings import settings

    parser.add_argument(
        "--base-url",
        default=f"{settings.default_base_url}/context",
        help="Base URL",
    )
    parser.add_argument("--token", help="Bearer token")
    args = parser.parse_args()
    client = SomaBrainClient(base_url=args.base_url, api_token=args.token)
    evaluation = client.evaluate(session_id=args.session, query=args.query)
    print("Prompt:\n", evaluation["prompt"])


if __name__ == "__main__":
    main()
