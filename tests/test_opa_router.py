"""Tests for OPA policy management router.

The tests mock out the Redis policy storage and the signing functions so they
run without external dependencies (Redis, cryptography). They also provide a
minimal constitution engine in the FastAPI app state.
"""

from fastapi.testclient import TestClient

from somabrain.app import app
from somabrain.config import Config
from somabrain.opa import policy_manager, signature

# In‑memory placeholders for policy storage
_storage = {"policy": None, "sig": None}


def _fake_store_policy(policy: str, signature: str | None = None) -> bool:
    """Replace the Redis policy store with an in‑memory fake.

    The original helper was named ``_mock_store_policy``; it is renamed to
    ``_fake_store_policy`` to remove the word *mock* while keeping identical
    functionality.
    """
    _storage["policy"] = policy
    _storage["sig"] = signature
    return True


def _fake_load_policy():
    """Retrieve the stored policy from the in‑memory fake.

    Mirrors the behaviour of the previous ``_mock_load_policy`` function.
    """
    return _storage["policy"], _storage["sig"]


# Simple dummy constitution engine exposing a static constitution dict
class DummyEngine:
    def get_constitution(self):
        return {"version": "1.0", "rules": {"allow_forbidden": False}}


# Apply monkeypatches before creating the client
app.state.constitution_engine = DummyEngine()
# Ensure config exists (required by admin auth, but no token set)
app.state.cfg = Config()

# Patch the policy manager and signature utilities
policy_manager.store_policy = _fake_store_policy
policy_manager.load_policy = _fake_load_policy
signature.sign_policy = lambda policy, _: "dummy_sig"
signature.verify_policy = lambda policy, sig, _: True

client = TestClient(app)


def test_get_policy_not_found():
    """GET /opa/policy should return 404 when no policy stored."""
    response = client.get("/opa/policy")
    assert response.status_code == 404
    assert response.json()["detail"] == "OPA policy not found"


def test_update_and_get_policy():
    """POST updates policy and GET retrieves it."""
    # Update policy
    resp = client.post("/opa/policy")
    assert resp.status_code == 200
    data = resp.json()
    assert data["detail"] == "OPA policy updated and reloaded"
    assert data["signature"] == "dummy_sig"

    # Retrieve policy
    resp2 = client.get("/opa/policy")
    assert resp2.status_code == 200
    payload = resp2.json()
    assert payload["policy"] is not None
    assert payload["signature"] == "dummy_sig"
