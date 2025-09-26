from __future__ import annotations

import importlib
import os
from typing import Dict

import pytest
import redis
import requests
from fastapi.testclient import TestClient

import somabrain.app as app_module


@pytest.fixture
def live_client(monkeypatch):
    redis_url = os.getenv("SOMA_REDIS_URL", "redis://127.0.0.1:6379/0")
    redis_client = redis.Redis.from_url(redis_url, socket_connect_timeout=1)
    try:
        redis_client.ping()
    except Exception:
        pytest.skip("NO_MOCKS: Redis not available")

    try:
        requests.get("http://127.0.0.1:8181/health", timeout=1)
    except Exception:
        pytest.skip("NO_MOCKS: OPA not available")

    kafka_bootstrap = os.getenv("SOMA_KAFKA_URL", "127.0.0.1:19092")

    try:
        requests.get("http://127.0.0.1:9595/health", timeout=1)
    except Exception:
        pytest.skip("NO_MOCKS: Memory service not available on 127.0.0.1:9595")

    monkeypatch.setenv("SOMABRAIN_MEMORY_HTTP_ENDPOINT", "http://127.0.0.1:9595")
    monkeypatch.setenv("SOMA_REDIS_URL", redis_url)
    monkeypatch.setenv("SOMA_KAFKA_URL", kafka_bootstrap)
    monkeypatch.setenv("SOMABRAIN_OPA_URL", "http://127.0.0.1:8181")
    monkeypatch.setenv("SOMABRAIN_REWARD_GATE_ENABLED", "true")
    monkeypatch.setenv("DISABLE_AUTH", "true")
    monkeypatch.setenv("SOMABRAIN_LOG_LEVEL", "error")

    importlib.reload(app_module)
    client = TestClient(app_module.app)
    redis_client.flushdb()
    try:
        yield client
    finally:
        client.close()
        importlib.reload(app_module)


@pytest.mark.integration
def test_reward_gate_metrics_increment(live_client: TestClient):
    metrics_before = live_client.get("/metrics").text

    response = live_client.post(
        "/recall",
        json={"query": "noop", "top_k": 1},
        headers={"X-Tenant-ID": "metrics-suite", "X-Utility-Value": "-1"},
    )
    assert response.status_code == 200

    metrics_after = live_client.get("/metrics").text
    assert "somabrain_reward_allow_total" in metrics_after
    assert "somabrain_reward_deny_total" in metrics_after

    allow_before = _extract_metric_value(metrics_before, "somabrain_reward_allow_total")
    allow_after = _extract_metric_value(metrics_after, "somabrain_reward_allow_total")
    deny_before = _extract_metric_value(metrics_before, "somabrain_reward_deny_total")
    deny_after = _extract_metric_value(metrics_after, "somabrain_reward_deny_total")

    assert allow_after > allow_before
    assert deny_after > deny_before


@pytest.mark.integration
def test_rag_pipeline_with_live_services(live_client: TestClient):
    tenant_headers: Dict[str, str] = {"X-Tenant-ID": "rag-live"}

    docs = [
        "solar grid sizing guide",
        "battery storage safety checklist",
    ]
    for doc in docs:
        resp = live_client.post(
            "/remember",
            json={"payload": {"task": doc, "memory_type": "episodic", "importance": 1}},
            headers=tenant_headers,
        )
        assert resp.status_code == 200

    metrics_before = _extract_metric_value(
        live_client.get("/metrics").text, "somabrain_rag_requests_total"
    )

    responses = []
    for payload in (
        {"query": "solar grid", "top_k": 5, "retrievers": ["vector"], "persist": False},
        {
            "query": "solar grid",
            "top_k": 5,
            "retrievers": ["vector", "wm"],
            "persist": True,
        },
        {"query": "solar grid", "top_k": 5, "retrievers": ["graph"], "persist": False},
    ):
        r = live_client.post("/rag/retrieve", json=payload, headers=tenant_headers)
        assert r.status_code == 200
        data = r.json()
        assert data.get("candidates")
        responses.append(data)

    graph_candidates = responses[-1]["candidates"]
    assert any(c.get("payload", {}).get("task") in docs for c in graph_candidates)

    metrics_after = _extract_metric_value(
        live_client.get("/metrics").text, "somabrain_rag_requests_total"
    )
    assert metrics_after >= metrics_before + 3.0


def _extract_metric_value(metrics_text: str, metric: str) -> float:
    from prometheus_client.parser import text_string_to_metric_families

    for family in text_string_to_metric_families(metrics_text):
        if family.name != metric:
            continue
        # Return the first sample value (no labels in use for these metrics)
        for sample in family.samples:
            if sample.name == metric:
                return float(sample.value)
    return 0.0
