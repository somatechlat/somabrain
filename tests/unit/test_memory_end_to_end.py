from fastapi.testclient import TestClient
from scripts.mock_memory import app

"""Simple end‑to‑end test for the mock memory HTTP service.

This test uses FastAPI's ``TestClient`` to exercise the ``/remember`` and
``/memory/get/{key}`` endpoints defined in ``scripts/mock_memory.py`` without
starting an external server process. It validates that a payload can be stored
and subsequently retrieved, providing a lightweight integration check that the
memory service behaves as expected.
"""


# Import the FastAPI app defined in the mock memory script.

client = TestClient(app)


def test_memory_remember_and_retrieve() -> None:
    """Store a payload via ``/remember`` and fetch it via ``/memory/get``.

    The mock service should echo back the stored JSON exactly.
    """
    payload = {"key": "test-key", "content": "hello world"}

    # POST the payload to the mock memory service.
    resp = client.post("/remember", json=payload)
    assert resp.status_code == 200, f"Unexpected status: {resp.status_code}"
    data = resp.json()
    assert data["status"] == "saved"
    assert data["key"] == payload["key"]

    # GET the same key back and verify the response matches the original payload.
    get_resp = client.get(f"/memory/get/{payload['key']}")
    assert get_resp.status_code == 200, f"GET failed: {get_resp.status_code}"
    assert get_resp.json() == payload
