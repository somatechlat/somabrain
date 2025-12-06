"""Test reconciliation of Oak options with Milvus.

These tests verify that the ``reconcile_milvus`` method correctly iterates
through known in-memory options and ensures they are persisted to the Milvus
backend.
"""

import pytest
import unittest.mock
from somabrain.oak.option_manager import OptionManager, Option

class MockMilvusClient:
    def __init__(self):
        self.upserts = []

    def upsert_option(self, tenant_id, option_id, payload):
        self.upserts.append((tenant_id, option_id, payload))

class MockMemoryClient:
    def remember(self, topic, key, value):
        pass

@pytest.fixture
def manager():
    # Patch clients to avoid external dependencies during unit test
    with unittest.mock.patch("somabrain.oak.option_manager.MilvusClient", return_value=MockMilvusClient()) as mock_milvus_cls, \
         unittest.mock.patch("somabrain.oak.option_manager.MemoryClient", return_value=MockMemoryClient()):

        mgr = OptionManager()
        # Since _milvus is a property that lazy-initializes, we need to inject the mock into the backing field directly.
        # But `OptionManager` sets `self._milvus_client = None` in init.
        # The property uses `self._milvus_client`.
        mgr._milvus_client = mock_milvus_cls.return_value
        return mgr

def test_reconcile_milvus_upserts_all_options(manager):
    """Verify that reconcile_milvus calls upsert for every option."""
    tenant = "test_tenant"

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

    # Verify upserts on the mock
    assert len(manager._milvus.upserts) == 2
    ids = sorted([call[1] for call in manager._milvus.upserts])
    assert ids == ["opt1", "opt2"]

def test_reconcile_handles_empty(manager):
    """Verify reconciliation handles empty tenant gracefully."""
    stats = manager.reconcile_milvus("empty_tenant")
    assert stats["checked"] == 0
    assert stats["repaired"] == 0
    assert len(manager._milvus.upserts) == 0
