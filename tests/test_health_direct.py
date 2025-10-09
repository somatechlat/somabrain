"""Direct health endpoint test using FastAPI's TestClient.

This test does not rely on an external uvicorn process. It imports the
application instance from ``somabrain.app`` and exercises the ``/health``
endpoint via ``TestClient``. The server logic (including configuration and
runtime singletons) is exercised in‑process, providing a genuine integration
test without the need for the background ``start_test_server.sh`` script.
"""

import pytest
from fastapi.testclient import TestClient

# Import the FastAPI app defined in the package.
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


def test_health_endpoint_returns_ok(client: TestClient):
    """Validate that ``/health`` returns a JSON payload with ``ok: true``.

    The response schema matches ``somabrain.schemas.HealthResponse`` – the test
    asserts the ``ok`` flag and checks that the ``components`` field is present.
    """
    response = client.get("/health")
    assert response.status_code == 200, "Health endpoint should be reachable"
    data = response.json()
    # The health response must contain the key ``ok`` set to True.
    assert data.get("ok") is True, "Health response must indicate ok=True"
    # Ensure the components dictionary is present (memory, wm_items, api_version).
    assert isinstance(data.get("components"), dict), "Components should be a dict"
