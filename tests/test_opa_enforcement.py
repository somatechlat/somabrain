from fastapi.testclient import TestClient

from somabrain.app import app
from somabrain.opa.client import opa_client

# Ensure the OPA middleware is active (registered during app import)
client = TestClient(app)


def test_opa_allows_request(monkeypatch):
    """When OPA returns allow=True the request should succeed (200)."""
    # Force OPA client to return True regardless of input
    monkeypatch.setattr(opa_client, "evaluate", lambda data: True)
    response = client.get("/health")  # simple endpoint that exists
    assert response.status_code == 200


def test_opa_denies_request(monkeypatch):
    """When OPA returns allow=False the request should be rejected with 403."""
    monkeypatch.setattr(opa_client, "evaluate", lambda data: False)
    response = client.get("/health")
    assert response.status_code == 403
    assert response.json()["detail"] == "OPA policy denied request"
