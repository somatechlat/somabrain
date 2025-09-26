import pytest




# Minimal app with only /context/feedback and all dependencies mocked

# Use the real app and dependencies, no overrides or mocks
def get_real_app():
    from somabrain.app import app as fastapi_app
    return fastapi_app

def test_feedback_audit_adaptation(monkeypatch):
    import os
    os.environ["DISABLE_AUTH"] = "true"
    from fastapi.testclient import TestClient
    app = get_real_app()
    client = TestClient(app)
    # Use real payload and real endpoint
    payload = {
        "session_id": "sess-1",
        "query": "test query",
        "prompt": "test prompt",
        "response_text": "test response",
        "utility": 1.0,
        "reward": 0.5,
        "metadata": {},
        "tenant_id": "sandbox",
    }
    client = TestClient(app)
    headers = {
        "X-Model-Confidence": "10.0",
        "X-Tenant-ID": "sandbox",
        # If your API requires an Authorization token, add it here:
        # "Authorization": "Bearer <your-token>"
    }
    r = client.post("/context/feedback", json=payload, headers=headers)
    if r.status_code != 200:
        print("RESPONSE:", r.status_code, r.text)
    assert r.status_code == 200
