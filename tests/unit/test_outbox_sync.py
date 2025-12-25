"""Integration-flavored checks for outbox sync helper using real services."""

from __future__ import annotations

import pytest
import httpx

from django.conf import settings
from somabrain.models import OutboxEvent
from somabrain.memory_client import MemoryClient
from somabrain.services.outbox_sync import _send_event


def _memory_available(url: str) -> bool:
    try:
        resp = httpx.get(url.rstrip("/") + "/health", timeout=2.0)
        return resp.status_code < 500
    except Exception:
        return False


# Use centralized Settings for test configuration
MEM_URL = settings.SOMABRAIN_MEMORY_HTTP_ENDPOINT or "http://localhost:9595"


@pytest.mark.asyncio
@pytest.mark.integration
async def test_send_event_success() -> None:
    """When the client reports success, ``_send_event`` returns ``True``."""
    if not _memory_available(MEM_URL):
        pytest.skip("Memory service not reachable for outbox sync tests")
    event = OutboxEvent(
        id=1,
        topic="memory_write",
        payload={"foo": "bar"},
        dedupe_key="key-1",
        tenant_id="test",
    )
    client = MemoryClient(settings)
    result = await _send_event(client, event)

    assert result is True


@pytest.mark.asyncio
@pytest.mark.integration
async def test_send_event_failure() -> None:
    """When the client reports failure, ``_send_event`` returns ``False``."""
    if not _memory_available(MEM_URL):
        pytest.skip("Memory service not reachable for outbox sync tests")
    # Use invalid payload to provoke failure
    event = OutboxEvent(
        id=2,
        topic="memory_write",
        payload={"foo": object()},  # not JSON serializable
        dedupe_key="key-2",
        tenant_id="test",
    )
    client = MemoryClient(settings)
    result = await _send_event(client, event)

    assert result is False
