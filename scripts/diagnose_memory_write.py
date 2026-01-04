"""Module diagnose_memory_write."""

import httpx
import json
import os

ENDPOINT = "http://localhost:10101"
TOKEN = "dev-token-somastack2024"

def try_store():
    """Execute try store.
        """

    url = f"{ENDPOINT}/memories"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "content": "Diagnostics Test Memory",
        "key": "diag-001",
        "namespace": "default"
    }
    print(f"POST {url}")
    try:
        r = httpx.post(url, json=payload, headers=headers, timeout=5.0)
        print(f"Status: {r.status_code}")
        print(f"Body: {r.text}")
    except Exception as e:
        print(f"Request Failed: {e}")

if __name__ == "__main__":
    try_store()