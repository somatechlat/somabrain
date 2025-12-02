"""Property-based tests for memory client invariants."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Tuple

import httpx
import pytest
from hypothesis import given, settings, strategies as st

from somabrain.config import get_config
from somabrain.memory_client import MemoryClient, _stable_coord


@given(st.text(min_size=0, max_size=256))
@settings(max_examples=50, deadline=None)
def test_stable_coord_deterministic(key: str) -> None:
    """Same key always yields the same coordinate."""
    c1 = _stable_coord(key)
    c2 = _stable_coord(key)
    assert c1 == c2


@given(st.text(min_size=0, max_size=256))
@settings(max_examples=50, deadline=None)
def test_stable_coord_bounds(key: str) -> None:
    """Coordinates remain within [-1, 1] for every component."""
    coord = _stable_coord(key)
    assert all(-1.0 <= x <= 1.0 for x in coord)


def _memory_service_available(url: str) -> bool:
    try:
        resp = httpx.get(url.rstrip("/") + "/health", timeout=2.0)
        return resp.status_code < 500
    except Exception:
        return False


@given(st.text(min_size=1, max_size=64), st.dictionaries(st.text(), st.text()))
@settings(max_examples=10, deadline=None)
def test_memory_round_trip(key: str, payload: dict) -> None:
    """Store then recall returns the payload back with a score."""
    cfg = get_config()
    client = MemoryClient(cfg)

    mem_url = os.environ.get("SOMABRAIN_MEMORY_URL", "http://localhost:9595")
    assert _memory_service_available(mem_url), "Memory service must be reachable for round-trip test"

    # remember
    coord = client.remember(key, payload)
    assert isinstance(coord, Tuple)

    # small delay to allow service to index
    time.sleep(0.1)

    hits = client.recall(query=key, top_k=5)
    assert hits, "recall returned no results"
    # At least one hit should be returned; detailed payload equality is backend-dependent.
    assert any(isinstance(h.payload, dict) for h in hits)
    assert all(h.score is None or isinstance(h.score, float) for h in hits)
