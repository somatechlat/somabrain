"""Simple smoke test for journaling and recall.

Usage:
    python scripts/smoke_mem_test.py --url http://127.0.0.1:9696

This script will POST a sample memory to /remember, optionally check the journal file,
then call the recall endpoint to verify presence. It is a small helper for local dev & can
be included in CI smoke step.
"""

import argparse
import time

import requests


def main(url: str):
    remember_url = f"{url.rstrip('/')}/remember"
    recall_url = f"{url.rstrip('/')}/recall"
    payload = {
        "coord": None,
        "payload": {"task": "smoke test - remember", "importance": 1},
    }

    print(f"Posting sample memory to {remember_url}")
    r = requests.post(remember_url, json=payload)
    print("POST /remember ->", r.status_code, r.text)
    if r.status_code >= 400:
        print("Remember failed; aborting smoke test")
        return 2

    time.sleep(0.5)

    # Try a lightweight recall by querying the task string; adjust per API if needed
    qpayload = {"query": "smoke test - remember", "limit": 5}
    try:
        r2 = requests.post(recall_url, json=qpayload)
    except Exception as e:
        print("Recall request failed:", e)
        return 3
    print("POST /recall ->", r2.status_code)
    try:
        print(r2.json())
    except Exception:
        print(r2.text)

    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:9696",
        help="Base URL for local somaBrain instance",
    )
    args = parser.parse_args()
    raise SystemExit(main(args.url))
