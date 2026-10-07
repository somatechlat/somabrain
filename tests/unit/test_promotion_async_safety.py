"""WM→LTM promotion must not touch Django ORM on the async path."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.no_django


def test_promotion_wraps_orm_in_sync_to_async() -> None:
    src = (Path(__file__).resolve().parents[2] / "somabrain" / "memory" / "promotion.py").read_text()
    assert "sync_to_async" in src
    assert "thread_sensitive=True" in src
    # create_link and _queue_to_outbox must be called under sync_to_async
    assert "await sync_to_async(self._queue_to_outbox" in src
    assert "await sync_to_async(_create_link" in src
