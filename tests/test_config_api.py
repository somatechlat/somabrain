from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from somabrain.api.config_api import router


@pytest.fixture
def client(monkeypatch) -> TestClient:
    async def _noop():
        return None

    monkeypatch.setattr("somabrain.api.config_api.ensure_config_dispatcher", _noop)
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def test_effective_config_and_cutover_flow(client: TestClient):

    # Fetch default config
    resp = client.get("/config/memory", params={"tenant": "acme", "namespace": "wm"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["tenant"] == "acme"
    assert body["namespace"] == "wm"
    assert isinstance(body["config"], dict)

    # Open a cutover plan
    open_resp = client.post(
        "/config/cutover/open",
        json={"tenant": "acme", "from_namespace": "wm", "to_namespace": "wm@v2"},
    )
    assert open_resp.status_code == 200
    plan = open_resp.json()["plan"]
    assert plan["status"] == "draft"

    # Record metrics to mark plan ready
    metrics_resp = client.post(
        "/config/cutover/metrics",
        json={
            "tenant": "acme",
            "namespace": "wm@v2",
            "top1_accuracy": 0.95,
            "margin": 0.2,
            "latency_p95_ms": 80.0,
        },
    )
    assert metrics_resp.status_code == 200
    plan = metrics_resp.json()["plan"]
    assert plan["ready"] is True

    # Approve plan
    approve_resp = client.post("/config/cutover/approve", json={"tenant": "acme"})
    assert approve_resp.status_code == 200
    assert approve_resp.json()["plan"]["status"] == "approved"

    # Execute plan
    execute_resp = client.post("/config/cutover/execute", json={"tenant": "acme"})
    assert execute_resp.status_code == 200
    assert execute_resp.json()["plan"]["status"] == "executed"
