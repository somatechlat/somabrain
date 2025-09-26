import pytest
from fastapi.testclient import TestClient

import somabrain.metrics as metrics
from somabrain.app import app
from somabrain.opa import client as opa_module


# Helper to reset counters by creating fresh registry (used in conftest otherwise)
@pytest.fixture(autouse=True)
def reset_registry():
    # Replace the global registry with a fresh one for isolation
    from prometheus_client import CollectorRegistry

    new_registry = CollectorRegistry()
    metrics.registry = new_registry
    # Recreate counters that depend on the registry
    metrics.OPA_ALLOW_TOTAL = metrics.get_counter(
        "somabrain_opa_allow_total",
        "Number of requests allowed by OPA",
    )
    metrics.OPA_DENY_TOTAL = metrics.get_counter(
        "somabrain_opa_deny_total",
        "Number of requests denied by OPA",
    )
    yield
    # No cleanup needed


client = TestClient(app)


def test_opa_allow_metric_increment(monkeypatch):
    # Force OPA to allow all requests
    monkeypatch.setattr(opa_module.opa_client, "evaluate", lambda _: True)
    # Capture initial counter value
    initial = metrics.OPA_ALLOW_TOTAL._value.get()
    response = client.get("/health")  # any endpoint that goes through middleware
    assert response.status_code == 200
    assert metrics.OPA_ALLOW_TOTAL._value.get() == initial + 1


def test_opa_deny_metric_increment(monkeypatch):
    # Force OPA to deny the request
    monkeypatch.setattr(opa_module.opa_client, "evaluate", lambda _: False)
    initial = metrics.OPA_DENY_TOTAL._value.get()
    response = client.get("/health")
    assert response.status_code == 403
    assert metrics.OPA_DENY_TOTAL._value.get() == initial + 1
