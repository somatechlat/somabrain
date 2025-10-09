"""Basic sanity checks for the live‑test FastAPI server.

The :func:`client` fixture (defined in ``tests/conftest.py``) provides an
``httpx.AsyncClient`` that is already configured to target the test server
running on ``http://localhost:9797`` (or whatever ``SOMA_API_URL`` is set to
by the fixtures).  These tests verify that the server starts correctly and
exposes the expected health endpoint.
"""

import pytest


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """Ensure ``/health`` returns a JSON payload with ``{"ok": true}``.

    The test does not mock any network interaction; it hits the real server
    started by the ``start_fastapi_server`` fixture in ``conftest.py``.
    """
    response = await client.get("/health")
    assert response.status_code == 200, "Health endpoint should be reachable"
    json_body = response.json()
    # The health endpoint returns a dict containing an ``ok`` key set to true.
    assert isinstance(json_body, dict)
    assert json_body.get("ok") is True
