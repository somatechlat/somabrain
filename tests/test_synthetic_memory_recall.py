"""End-to-end regression against the live Somabrain deployment.

This test suite exercises the publicly exposed Somabrain API running on
``SOMA_API_URL`` (default ``http://localhost:9696``) and asserts that persona
data is persisted and retrieved via the real SomaMemory service running on
port 9595.  No mocks or local simulators are involved.
"""

from __future__ import annotations

import os
import uuid

import requests

from somabrain.testing.synthetic_memory import (
    require_http_service,
    require_tcp_endpoint,
)

API_BASE = os.getenv("SOMA_API_URL", "http://localhost:9696")
MEMORY_BASE = os.getenv("SOMABRAIN_MEMORY_HTTP_ENDPOINT", "http://localhost:9595")
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
def test_persona_round_trip_against_live_stack():
    """Write, read, and clean up a persona record using the live stack."""

    require_tcp_endpoint(REDIS_HOST, REDIS_PORT)
    require_http_service(API_BASE, "/demo")  # quick check that 9696 is reachable
    require_http_service(MEMORY_BASE)

    persona_id = f"integration-{uuid.uuid4().hex[:12]}"
    payload = {
        "display_name": "Integration Test Persona",
        "properties": {"origin": "integration-test", "persona_id": persona_id},
    }

    put_resp = requests.put(
        f"{API_BASE}/persona/{persona_id}",
        json=payload,
        timeout=10,
    )
    assert put_resp.status_code == 200, put_resp.text

    get_resp = requests.get(
        f"{API_BASE}/persona/{persona_id}",
        timeout=10,
    )
    assert get_resp.status_code == 200, get_resp.text
    body = get_resp.json()
    assert body["display_name"] == payload["display_name"]
    assert body["properties"]["persona_id"] == persona_id

    recall_resp = requests.post(
        f"{MEMORY_BASE}/recall",
        json={"query": persona_id, "top_k": 50},
        timeout=10,
    )
    assert recall_resp.status_code == 200, recall_resp.text
    memories = recall_resp.json()
    assert any(m.get("id") == persona_id for m in memories), "Persona not stored in SomaMemory"

    delete_resp = requests.delete(
        f"{API_BASE}/persona/{persona_id}",
        timeout=10,
    )
    assert delete_resp.status_code == 200, delete_resp.text
