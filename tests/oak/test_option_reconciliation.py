"""Test reconciliation of Oak options with Milvus.

These tests verify that the ``reconcile_milvus`` method correctly iterates
through known in-memory options and ensures they are persisted to the Milvus
backend.

VIBE Compliance:
- No mocks/patches used.
- Uses dependency injection with local fake implementations.
"""

import pytest
from typing import Dict, List, Tuple
from somabrain.oak.option_manager import OptionManager, Option

# --- Fakes for Dependency Injection ---

class FakeMilvusClient:
    """A fake Milvus client that stores upserts in memory."""
    def __init__(self):
        # Store upserts as (tenant_id, option_id, payload) tuples
        self.upserts: List[Tuple[str, str, bytes]] = []

    def upsert_option(self, tenant_id: str, option_id: str, payload: bytes) -> None:
        self.upserts.append((tenant_id, option_id, payload))

class FakeMemoryClient:
    """A fake Memory client that ignores calls (stub behavior for test isolation)."""
    def __init__(self, cfg=None):
        pass

    def remember(self, topic: str, key: str, value: bytes) -> None:
        pass

# --- Tests ---

def test_reconcile_milvus_upserts_all_options():
    """Verify that reconcile_milvus calls upsert for every option using DI fakes."""
    tenant = "test_tenant"

    # Instantiate fakes
    fake_milvus = FakeMilvusClient()
    fake_memory = FakeMemoryClient()

    # Inject fakes into OptionManager
    manager = OptionManager(memory_client=fake_memory, milvus_client=fake_milvus)

    # Pre-populate manager store manually to simulate "memory" state
    opt1 = Option(option_id="opt1", tenant_id=tenant, payload=b"data1")
    opt2 = Option(option_id="opt2", tenant_id=tenant, payload=b"data2")

    manager._store[tenant] = {
        "opt1": opt1,
        "opt2": opt2
    }

    # Run reconciliation
    stats = manager.reconcile_milvus(tenant)

    assert stats["checked"] == 2
    assert stats["repaired"] == 2

    # Verify upserts on the fake Milvus client
    assert len(fake_milvus.upserts) == 2
    ids = sorted([call[1] for call in fake_milvus.upserts])
    assert ids == ["opt1", "opt2"]

def test_reconcile_handles_empty():
    """Verify reconciliation handles empty tenant gracefully."""
    fake_milvus = FakeMilvusClient()
    fake_memory = FakeMemoryClient()
    manager = OptionManager(memory_client=fake_memory, milvus_client=fake_milvus)

    stats = manager.reconcile_milvus("empty_tenant")

    assert stats["checked"] == 0
    assert stats["repaired"] == 0
    assert len(fake_milvus.upserts) == 0
