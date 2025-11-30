"""Unit tests for the outbox synchronization worker.

These tests verify the core helper ``_send_event`` without requiring a real
database or external memory service. They mock ``MemoryClient._store_http_sync``
to return success or failure and assert that the function returns the expected
boolean value.

All code follows the VIBE CODING RULES: full type hints, docstrings, no
place‑holders, and deterministic behavior.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Dict

import pytest

# Import the private helper from the outbox sync module.
from somabrain.services.outbox_sync import _send_event


@dataclass
class DummyEvent:
    """Minimal stub mimicking ``OutboxEvent`` used by the sync worker."""

    id: int
    payload: Dict[str, Any]
    dedupe_key: str
    status: str = "pending"
    retries: int = 0


class DummyClient:
    """Mock ``MemoryClient`` exposing only the ``_store_http_sync`` method.

    The ``_store_http_sync`` method is configured via the ``should_succeed``
    flag to simulate both success and failure scenarios.
    """

    def __init__(self, should_succeed: bool = True):
        self._should_succeed = should_succeed

    def _store_http_sync(self, body: dict, headers: dict) -> tuple[bool, Any]:  # pragma: no cover
        # The real implementation returns ``(success, response)``.
        return (self._should_succeed, {"mock": "response"})


@pytest.mark.asyncio
async def test_send_event_success() -> None:
    """When the client reports success, ``_send_event`` returns ``True``."""

    event = DummyEvent(id=1, payload={"foo": "bar"}, dedupe_key="key-1")
    client = DummyClient(should_succeed=True)
    result = await _send_event(client, event)
    assert result is True


@pytest.mark.asyncio
async def test_send_event_failure() -> None:
    """When the client reports failure, ``_send_event`` returns ``False``."""

    event = DummyEvent(id=2, payload={"baz": 123}, dedupe_key="key-2")
    client = DummyClient(should_succeed=False)
    result = await _send_event(client, event)
    assert result is False
