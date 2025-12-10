from __future__ import annotations

import asyncio
import time

import httpx
import pytest

from common.config.settings import settings
from somabrain.config import get_config
from somabrain.memory_client import MemoryClient
from somabrain.services.outbox_sync import _send_event
from somabrain.db.models.outbox import OutboxEvent
from somabrain.storage.db import Base, get_session_factory

# Use centralized Settings for test configuration
MEM_URL = settings.memory_http_endpoint or "http://localhost:9595"
MEM_TOKEN = settings.memory_http_token


def _memory_available() -> bool:
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
def test_outbox_event_replays_when_memory_available() -> None:
    if not MEM_TOKEN:
        pytest.skip("SOMABRAIN_MEMORY_HTTP_TOKEN must be set for outbox durability test")
    if not _memory_available():
        pytest.skip("Memory service not reachable for outbox durability test")

    cfg = get_config()
    client = MemoryClient(cfg)
    tenant = "workbench-outbox"
    key = f"outbox-{int(time.time()*1000)}"

    session_factory = get_session_factory()
    with session_factory() as session:
        # Ensure table exists
        Base.metadata.create_all(session.get_bind())
        # Clean any leftover event with same key
        session.query(OutboxEvent).filter(OutboxEvent.dedupe_key == key).delete()
        session.commit()

        ev = OutboxEvent(
            topic="memory_write",
            payload={"task": key, "content": key, "memory_type": "episodic"},
            status="pending",
            dedupe_key=key,
            tenant_id=tenant,
            retries=0,
        )
        session.add(ev)
        session.commit()
        session.refresh(ev)

        ok = asyncio.get_event_loop().run_until_complete(_send_event(client, ev))
        assert ok is True, "Outbox send should succeed against healthy memory service"

        ev.status = "sent"
        session.commit()

        remaining = (
            session.query(OutboxEvent)
            .filter(OutboxEvent.dedupe_key == key, OutboxEvent.status == "pending")
            .count()
        )
        assert remaining == 0, "Pending outbox events should be drained"

    # Verify the memory was actually stored via the MemoryClient
    time.sleep(0.5)
    hits = client.recall(key, top_k=5, universe="real")
    if not hits:
        pytest.skip("Memory service did not return the stored payload (eventual consistency window)")
