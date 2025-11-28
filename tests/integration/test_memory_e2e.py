"""Integration test for the real memory service.

This test exercises the :class:`~somabrain.memory_client.MemoryClient` against a
live HTTP memory backend. It stores a simple payload and then performs a recall
query that should return the stored memory. The test is deliberately minimal –
its purpose is to verify end‑to‑end connectivity without mocking any part of
the stack.

The test expects the environment variable ``SOMABRAIN_MEMORY_HTTP_ENDPOINT``
to point at a running memory service (default ``http://localhost:9595``). If the
service is unavailable the test will be skipped.
"""

import time
import pytest

from somabrain.memory_client import MemoryClient, RecallHit
from common.config.settings import settings


def _service_available() -> bool:
    """Quick check that the HTTP endpoint is reachable.

    A ``HEAD`` request is sufficient and inexpensive. If the request raises an
    exception we treat the service as unavailable and skip the test.
    """
    endpoint = getattr(settings, "memory_http_endpoint", "http://localhost:9595")
    try:
        import httpx

        with httpx.Client(base_url=endpoint, timeout=2.0) as client:
            resp = client.head("/")
            return resp.status_code < 500
    except Exception:
        return False


@pytest.mark.integration
@pytest.mark.skipif(not _service_available(), reason="Memory HTTP service not reachable")
def test_memory_remember_and_recall() -> None:
    """Store a payload and verify it can be recalled.

    The test performs the following steps:
    1. Creates a ``MemoryClient`` using the global ``settings`` instance.
    2. Calls :meth:`MemoryClient.remember` with a deterministic key and payload.
    3. Sleeps briefly to allow the asynchronous backend to index the new memory.
    4. Calls :meth:`MemoryClient.recall` with a query that should match the
       stored content and asserts that the payload appears in the results.
    """
    client = MemoryClient(cfg=settings)

    test_key = "e2e-test-key"
    payload = {"key": test_key, "content": "hello world"}

    # Store the memory – ``remember`` returns the coordinate tuple.
    coord = client.remember(coord_key=test_key, payload=payload)
    assert isinstance(coord, tuple) and len(coord) == 3

    # Give the service a moment to make the memory searchable.
    time.sleep(0.5)

    # Recall using a query that should match the ``content`` field.
    hits: list[RecallHit] = client.recall(query="hello", top_k=5)
    assert any(hit.payload.get("key") == test_key for hit in hits), "Stored memory not found in recall results"
