"""Unit tests for the outbox synchronization worker.

These tests verify the core helper ``_send_event`` using real but local/in-memory implementations.
The tests use dependency injection where possible or lightweight local classes.

All code follows the VIBE CODING RULES: full type hints, docstrings, no
place‑holders, and deterministic behavior.
"""

from __future__ import annotations

import pytest
from typing import Any, Tuple

# Use the real OutboxEvent class if possible, or a compatible dataclass if not easily instantiable without DB.
# Assuming OutboxEvent is a SQLAlchemy model, we can instantiate it directly.
from somabrain.db.outbox import OutboxEvent

# Import the private helper from the outbox sync module.
from somabrain.services.outbox_sync import _send_event


class LocalMemoryClient:
    """Local, functional implementation of MemoryClient for testing.

    This class implements the `_store_http_sync` contract
    deterministically based on initialization parameters.
    """

    def __init__(self, succeed: bool = True):
        self._succeed = succeed
        self.last_stored_body = None

    def _store_http_sync(self, body: dict, headers: dict) -> Tuple[bool, Any]:
        """Real implementation of the storage interface for testing."""
        if self._succeed:
            self.last_stored_body = body
            return (True, {"status": "ok", "id": "local-123"})
        else:
            return (False, {"status": "error", "reason": "simulated failure"})


@pytest.mark.asyncio
async def test_send_event_success() -> None:
    """When the client reports success, ``_send_event`` returns ``True``."""

    # Use real OutboxEvent model
    event = OutboxEvent(
        id=1, payload={"foo": "bar"}, dedupe_key="key-1", status="pending", retries=0
    )

    # Use local functional client
    client = LocalMemoryClient(succeed=True)

    result = await _send_event(client, event)

    assert result is True
    assert client.last_stored_body is not None
    # Verify payload structure matches what _send_event constructs
    # Corrected keys to match somabrain/services/outbox_sync.py logic:
    # body = { "key": event.dedupe_key, "value": event.payload, "universe": ... }
    assert client.last_stored_body["value"] == {"foo": "bar"}
    assert client.last_stored_body["key"] == "key-1"


@pytest.mark.asyncio
async def test_send_event_failure() -> None:
    """When the client reports failure, ``_send_event`` returns ``False``."""

    event = OutboxEvent(
        id=2, payload={"baz": 123}, dedupe_key="key-2", status="pending", retries=0
    )

    client = LocalMemoryClient(succeed=False)

    result = await _send_event(client, event)

    assert result is False
    assert client.last_stored_body is None
