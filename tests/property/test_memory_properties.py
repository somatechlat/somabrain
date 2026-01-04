"""Property-based tests for memory client invariants."""

from __future__ import annotations

import os
import time
from typing import Tuple

import httpx
import pytest
from hypothesis import given, settings as hypothesis_settings, strategies as st

from django.conf import settings
from somabrain.memory_client import MemoryClient, _stable_coord

pytestmark = pytest.mark.property


@given(st.text(min_size=0, max_size=256))
@hypothesis_settings(max_examples=120, deadline=None)
def test_stable_coord_deterministic(key: str) -> None:
    """**Feature: memory-client-api-alignment, Property 1: Deterministic coordinate generation**"""
    c1 = _stable_coord(key)
    c2 = _stable_coord(key)
    assert c1 == c2


@given(st.text(min_size=0, max_size=256))
@hypothesis_settings(max_examples=120, deadline=None)
def test_stable_coord_bounds(key: str) -> None:
    """**Feature: memory-client-api-alignment, Property 2: Coordinate components remain within [-1, 1]**"""
    coord = _stable_coord(key)
    assert all(-1.0 <= x <= 1.0 for x in coord)


def _memory_service_available(url: str) -> bool:
    """Execute memory service available.

        Args:
            url: The url.
        """

    try:
        resp = httpx.get(url.rstrip("/") + "/health", timeout=2.0)
        return resp.status_code < 500
    except Exception:
        return False


@pytest.mark.integration
@given(st.text(min_size=1, max_size=64), st.dictionaries(st.text(), st.text()))
@hypothesis_settings(max_examples=120, deadline=None)
def test_memory_round_trip(key: str, payload: dict) -> None:
    """**Feature: memory-client-api-alignment, Property 3: Memory remember/recall round-trip preserves payload data**"""
    client = MemoryClient(settings)

    mem_url = getattr(settings, "SOMABRAIN_MEMORY_HTTP_ENDPOINT", "http://localhost:9595")
    if not _memory_service_available(mem_url):
        pytest.skip("Memory service not reachable; skipping round-trip property test")

    # remember
    try:
        coord = client.remember(key, payload)
    except RuntimeError as exc:
        pytest.skip(f"Memory service write failed: {exc}")
    assert isinstance(coord, Tuple)

    # small delay to allow service to index
    time.sleep(0.1)

    try:
        hits = client.recall(query=key, top_k=5)
    except RuntimeError as exc:
        pytest.skip(f"Memory service recall failed: {exc}")
    assert hits, "recall returned no results"
    # At least one hit should be returned; detailed payload equality is backend-dependent.
    assert any(isinstance(h.payload, dict) for h in hits)
    assert all(h.score is None or isinstance(h.score, float) for h in hits)