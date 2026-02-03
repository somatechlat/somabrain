"""Integration-flavored checks for outbox sync helper using real services."""

from __future__ import annotations

import pytest
import httpx

from django.conf import settings
from somabrain.apps.core.models import OutboxEvent
from somabrain.memory.client import MemoryClient
from somabrain.services.outbox_sync import _send_event


def _memory_available(url: str) -> bool:
    """Execute memory available.

    Args:
        url: The url.
    """

    try:
        resp = httpx.get(url.rstrip("/") + "/health", timeout=2.0)
        return resp.status_code < 500
    except Exception:
        return False


# Use centralized Settings for test configuration
MEM_URL = settings.SOMABRAIN_MEMORY_HTTP_ENDPOINT or "http://localhost:9595"


@pytest.fixture
def auth_settings():
    """Execute auth settings."""

    from tests.integration.infra_config import AUTH

    class ConfigProxy:
        """Configproxy class implementation."""

        def __init__(self):
            # transport.py expects 'memory_http_token' and 'memory_http_endpoint'
            """Initialize the instance."""

            self.memory_http_token = AUTH["api_token"]
            self.memory_http_endpoint = "http://127.0.0.1:10101"
            # Keep prefixed versions just in case other parts use them
            self.SOMABRAIN_MEMORY_HTTP_ENDPOINT = "http://127.0.0.1:10101"

    return ConfigProxy()


@pytest.mark.asyncio
@pytest.mark.integration
async def test_send_event_success(auth_settings) -> None:
    """When the client reports success, ``_send_event`` returns ``True``."""
    if not _memory_available("http://127.0.0.1:10101"):
        pytest.skip("Memory service not reachable for outbox sync tests")

    # Needs a valid payload structure: {coord, payload, memory_type}
    # But _send_event might wrap it? No, OutboxEvent payload IS the body.
    # Updated Payload for SFM v0.2
    event = OutboxEvent(
        id=1,
        topic="memory_write",
        payload={
            "coord": "0,0,0",
            "payload": {"content": "outbox_test"},
            "memory_type": "episodic",
        },
        dedupe_key="key-1",
        tenant_id="test",
    )
    client = MemoryClient(auth_settings)
    result = await _send_event(client, event)
    # Debug if false
    if not result:
        print("DEBUG: _send_event failed. Check SFM logs or Auth.")

    assert result is True


@pytest.mark.asyncio
@pytest.mark.integration
async def test_send_event_failure(auth_settings) -> None:
    """When the client reports failure, ``_send_event`` returns ``False``."""
    if not _memory_available("http://127.0.0.1:10101"):
        pytest.skip("Memory service not reachable for outbox sync tests")
    # Use invalid payload to provoke failure (non-serializable)
    event = OutboxEvent(
        id=2,
        topic="memory_write",
        payload={"foo": object()},  # not JSON serializable
        dedupe_key="key-2",
        tenant_id="test",
    )
    client = MemoryClient(auth_settings)
    # This should fail due to serialization or API rejection
    # Actually _send_event catches exceptions and returns False?
    try:
        result = await _send_event(client, event)
    except Exception:
        result = False

    assert result is False
