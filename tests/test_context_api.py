from fastapi import FastAPI
from fastapi.testclient import TestClient

from somabrain.api.context_route import router, _feedback_store, _token_ledger
from somabrain.api.dependencies.utility_guard import utility_guard
from somabrain.api.dependencies.auth import auth_guard, set_auth_config
from somabrain.config import Config


def test_evaluate_and_feedback(monkeypatch):
    set_auth_config(Config(sandbox_tenants=["sandbox", "tenant-alpha"]))
    app = FastAPI()
    app.dependency_overrides[utility_guard] = lambda: None
    app.dependency_overrides[auth_guard] = lambda: None
    app.include_router(router, prefix="/context")

    client = TestClient(app)

    resp = client.post(
        "/context/evaluate",
        json={"session_id": "sess", "query": "What is Soma?", "top_k": 2},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["query"] == "What is Soma?"
    assert body["tenant_id"] == "sandbox"
    assert "prompt" in body
    assert isinstance(body["memories"], list)

    feedback = client.post(
        "/context/feedback",
        json={
            "session_id": "sess",
            "query": body["query"],
            "prompt": body["prompt"],
            "response_text": "Answer",
            "utility": 0.5,
            "reward": 0.2,
            "metadata": {"tokens": 42, "model": "stub"},
        },
    )
    assert feedback.status_code == 200, feedback.text
    assert feedback.json()["accepted"] is True

    records = _feedback_store.list_for_session("sess")
    assert records

    token_records = _token_ledger.list_for_session("sess")
    assert any(abs(r.tokens - 42) < 1e-6 for r in token_records)
