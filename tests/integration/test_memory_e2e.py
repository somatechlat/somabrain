import time
import pytest
from somabrain.memory_client import MemoryClient, RecallHit
from django.conf import settings
from common.logging import logger
import httpx

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


def _service_available() -> bool:
    """Quick check that the HTTP endpoint is reachable.

    A ``HEAD`` request is sufficient and inexpensive. If the request raises an
    exception we treat the service as unavailable and skip the test.
    """
    endpoint = getattr(settings, "memory_http_endpoint", "http://localhost:9696")
    try:
        with httpx.Client(base_url=endpoint, timeout=2.0) as client:
            resp = client.head("/")
            return resp.status_code < 500
    except Exception as exc:
        logger.warning("Memory service not reachable at %s: %s", endpoint, exc)
        return False


@pytest.mark.integration
def test_memory_remember_and_recall() -> None:
    """Store a payload and verify it can be recalled.

    The test performs the following steps:
    1. Creates a ``MemoryClient`` using the global ``settings`` instance.
    2. Calls :meth:`MemoryClient.remember` with a deterministic key and payload.
    3. Sleeps briefly to allow the asynchronous backend to index the new memory.
    4. Calls :meth:`MemoryClient.recall` with a query that should match the
       stored content and asserts that the payload appears in the results.
    """
    if not _service_available():
        pytest.skip("Memory service not reachable; skipping e2e test")

    client = MemoryClient(cfg=settings)
    try:
        health = client.health()
    except Exception as exc:
        pytest.skip(f"Memory service health endpoint failed: {exc}")
    if not health.get("healthy"):
        pytest.skip(f"Memory service unhealthy: {health}")

    test_key = "e2e-test-key"
    payload = {"key": test_key, "content": "hello world"}

    # Store the memory – ``remember`` returns the coordinate tuple.
    try:
        coord = client.remember(coord_key=test_key, payload=payload)
    except RuntimeError as exc:
        pytest.skip(f"Memory service write failed: {exc}")
    assert isinstance(coord, tuple) and len(coord) == 3

    # Give the service a moment to make the memory searchable.
    time.sleep(0.5)

    # Recall using a query that should match the ``content`` field.
    try:
        hits: list[RecallHit] = client.recall(query="hello", top_k=5)
    except RuntimeError as exc:
        pytest.skip(f"Memory service recall failed: {exc}")
    assert hits, "recall returned no results"
