"""Direct health endpoint test using FastAPI's TestClient.

This test does not rely on an external uvicorn process. It imports the
application instance from ``somabrain.app`` and exercises the ``/health``
endpoint via ``TestClient``. The server logic (including configuration and
runtime singletons) is exercised in‑process, providing a genuine integration
test without the need for the background ``start_test_server.sh`` script.
"""

import pytest
from fastapi.testclient import TestClient

from somabrain import metrics as M
from somabrain.app import app


@pytest.fixture(scope="module")
def client():
    """Create a TestClient for the FastAPI app.

    The fixture yields a client that can be reused across multiple tests in the
    module. ``TestClient`` runs the app in the same process, so no external
    server is required.
    """
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def reset_metrics_gate():
    """Ensure external metrics readiness state is clean for each test."""

    M.reset_external_metrics()
    yield
    M.reset_external_metrics()


def test_health_requires_external_metrics(client: TestClient):
    """Health should report not-ready until exporters have been scraped."""

    response = client.get("/health")
    assert response.status_code == 200, "Health endpoint should be reachable"
    data = response.json()
    assert data.get("ok") is False, "Metrics gate should prevent ok before scrape"
    assert data.get("ready") is False, "Readiness should remain false until scrape"
    assert data.get("metrics_ready") is False, "Metrics gate flag should be false"
    assert "observability_metrics_missing" in data.get("alerts", []), (
        "Missing metrics should raise an alert"
    )


def test_health_ok_after_metrics_scrape(client: TestClient):
    """Once Kafka/Postgres/OPA metrics scrape, health should pass."""

    for source in ("kafka", "postgres", "opa"):
        M.mark_external_metric_scraped(source)
    response = client.get("/health")
    assert response.status_code == 200, "Health endpoint should be reachable"
    data = response.json()
    assert data.get("ok") is True, "System should report ok after metrics scrape"
    assert data.get("ready") is True, "Readiness should be true after metrics scrape"
    assert data.get("metrics_ready") is True, "Metrics gate flag should be true"
    assert isinstance(data.get("components"), dict), "Components should be a dict"
