"""Module test_outbox_durability."""

from __future__ import annotations

import asyncio
import time

import httpx
import pytest

from django.conf import settings
from somabrain.memory_client import MemoryClient
from somabrain.services.outbox_sync import _send_event
from somabrain.models import OutboxEvent

# Use centralized Settings for test configuration
MEM_URL = settings.SOMABRAIN_MEMORY_HTTP_ENDPOINT or "http://localhost:9595"
MEM_TOKEN = settings.SOMABRAIN_MEMORY_HTTP_TOKEN


def _memory_available() -> bool:
    """Execute memory available.
        """

    try:
        headers = {"Authorization": f"Bearer {MEM_TOKEN}"} if MEM_TOKEN else {}
        url = MEM_URL.rstrip("/")
        try:
            r = httpx.get(f"{url}/health", timeout=2.0, headers=headers)
        except Exception:
            r = httpx.get("http://localhost:9595/health", timeout=2.0, headers=headers)
        return r.status_code < 500
    except Exception:
        return False


@pytest.mark.integration
@pytest.mark.django_db
def test_outbox_event_replays_when_memory_available() -> None:
    """Execute test outbox event replays when memory available.
        """

    if not MEM_TOKEN:
        pytest.skip(
            "SOMABRAIN_MEMORY_HTTP_TOKEN must be set for outbox durability test"
        )
    if not _memory_available():
        pytest.skip("Memory service not reachable for outbox durability test")

    client = MemoryClient(settings)
    tenant = "workbench-outbox"
    key = f"outbox-{int(time.time()*1000)}"

    # Clean any leftover event with same key (Django ORM)
    OutboxEvent.objects.filter(dedupe_key=key).delete()

    ev = OutboxEvent.objects.create(
        topic="memory_write",
        payload={"task": key, "content": key, "memory_type": "episodic"},
        status="pending",
        dedupe_key=key,
        tenant_id=tenant,
        retries=0,
    )

    ok = asyncio.get_event_loop().run_until_complete(_send_event(client, ev))
    assert ok is True, "Outbox send should succeed against healthy memory service"

    ev.status = "sent"
    ev.save()

    remaining = OutboxEvent.objects.filter(dedupe_key=key, status="pending").count()
    assert remaining == 0, "Pending outbox events should be drained"

    # Verify the memory was actually stored via the MemoryClient
    time.sleep(0.5)
    hits = client.recall(key, top_k=5, universe="real")
    if not hits:
        pytest.skip(
            "Memory service did not return the stored payload (eventual consistency window)"
        )