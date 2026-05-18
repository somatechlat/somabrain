"""Module diagnose_memory_write."""

import os

import httpx

ENDPOINT = os.getenv("SOMABRAIN_MEMORY_HTTP_ENDPOINT", "http://localhost:10101")
TOKEN = os.getenv("SOMABRAIN_MEMORY_HTTP_TOKEN", "")


def try_store():
    """Execute try store."""

    url = f"{ENDPOINT}/memories"
    headers = {"Content-Type": "application/json"}
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    payload = {
        "content": "Diagnostics Test Memory",
        "key": "diag-001",
        "namespace": "default",
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
