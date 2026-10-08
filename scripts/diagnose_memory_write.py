"""Diagnostics: POST a probe memory via Vault-resolved credentials (Art 26).

Never reads secrets from environment variables.
"""

from __future__ import annotations

import httpx


def _endpoint() -> str:
    from django.conf import settings

    return str(getattr(settings, "SOMABRAIN_MEMORY_HTTP_ENDPOINT", "")).rstrip("/")


def _token() -> str:
    try:
        from somabrain.memory.sfm_auth import resolve_sfm_api_token

        return str(resolve_sfm_api_token() or "")
    except Exception:
        return ""


def try_store() -> None:
    """Execute try_store."""

    url = f"{_endpoint()}/memories"
    headers = {"Content-Type": "application/json"}
    token = _token()
    if not token:
        print("FAIL: no Vault-resolved SOMA token (Art 26 — no env fallback)")
        return
    headers["Authorization"] = f"Bearer {token}"
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
