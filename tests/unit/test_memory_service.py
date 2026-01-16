"""Unit tests for MemoryService helper methods.

These tests require a real memory backend to be available.
Tests are skipped when the backend is unavailable.
"""

from __future__ import annotations

import pytest

from somabrain.services.memory_service import MemoryService


def _backend_available() -> bool:
    """Check if memory backend is available for testing."""
    try:
        from django.conf import settings
        from somabrain.memory_pool import MultiTenantMemory

        # Try to create a real backend
        mt_memory = MultiTenantMemory(settings, scorer=None, embedder=None)
        client = mt_memory.for_namespace("test:unit")
        if client is None:
            return False
        # Actually check if the backend is healthy
        health = client.health()
        return health.get("kv_store", False) or health.get("vector_store", False)
    except Exception:
        return False


@pytest.fixture
def memory_service():
    """Create a real MemoryService instance or skip if unavailable."""
    if not _backend_available():
        pytest.skip("Memory backend not available for unit tests")

    from django.conf import settings
    from somabrain.memory_pool import MultiTenantMemory

    mt_memory = MultiTenantMemory(settings, scorer=None, embedder=None)
    return MemoryService(mt_memory, "test:unit")


@pytest.mark.skipif(not _backend_available(), reason="Memory backend not available")
def test_recall_with_scores_returns_results(memory_service: MemoryService) -> None:
    """Test that recall_with_scores returns results from real backend."""
    # This test validates the method exists and returns expected structure
    hits = memory_service.recall_with_scores("test query", top_k=2, universe=None)

    # Results should be a list (may be empty if no data)
    assert isinstance(hits, list)

    # If results exist, verify structure
    for hit in hits:
        assert isinstance(hit, dict)
        assert "payload" in hit or "score" in hit


@pytest.mark.skipif(not _backend_available(), reason="Memory backend not available")
@pytest.mark.asyncio
async def test_arecall_with_scores_returns_results(
    memory_service: MemoryService,
) -> None:
    """Test that arecall_with_scores returns results from real backend."""
    hits = await memory_service.arecall_with_scores("test query", top_k=1, universe=None)

    # Results should be a list (may be empty if no data)
    assert isinstance(hits, list)

    # If results exist, verify structure
    for hit in hits:
        assert isinstance(hit, dict)
