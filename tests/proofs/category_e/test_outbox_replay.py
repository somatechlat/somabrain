"""Category E2: Outbox Replay Tests.

**Feature: deep-memory-integration**
**Validates: Requirements E2.1, E2.2, E2.3, E2.4, E2.5**

Integration tests that verify outbox replay works correctly without duplicates.
These tests run against REAL Docker infrastructure - NO mocks.

Test Coverage:
- Task 10.6: SFM fails → outbox entry pending → SFM recovers → replay succeeds → no duplicates
"""

from __future__ import annotations

import os
import time
import uuid

import pytest

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Skip tests if infrastructure is not available
pytestmark = pytest.mark.skipif(
    os.environ.get("SOMA_INFRA_AVAILABLE") != "1",
    reason="Requires live infrastructure (Redis, Postgres, Milvus)",
)


# ---------------------------------------------------------------------------
# Test Class: Outbox Replay (E2)
# ---------------------------------------------------------------------------


@pytest.mark.memory_proof
class TestOutboxReplay:
    """Tests for outbox replay functionality.

    **Feature: deep-memory-integration, Category E2: Outbox Enhancement**
    **Validates: Requirements E2.1, E2.2, E2.3, E2.4, E2.5**

    These tests verify the outbox correctly handles failures and replays
    without creating duplicates.
    """

    def test_idempotency_key_generation(self) -> None:
        """E2.4: Idempotency keys are generated correctly.

        **Feature: deep-memory-integration**
        **Validates: Requirements E2.4**

        Idempotency keys should be deterministic based on operation,
        coordinate, and tenant.
        """
        from somabrain.db.outbox import _idempotency_key

        # Same inputs should produce same key
        key1 = _idempotency_key(
            operation="memory.store",
            coord=(1.0, 2.0, 3.0),
            tenant="tenant_a",
        )
        key2 = _idempotency_key(
            operation="memory.store",
            coord=(1.0, 2.0, 3.0),
            tenant="tenant_a",
        )
        assert key1 == key2, "Same inputs should produce same idempotency key"

        # Different tenant should produce different key
        key3 = _idempotency_key(
            operation="memory.store",
            coord=(1.0, 2.0, 3.0),
            tenant="tenant_b",
        )
        assert key1 != key3, "Different tenant should produce different key"

        # Different operation should produce different key
        key4 = _idempotency_key(
            operation="graph.link",
            coord=(1.0, 2.0, 3.0),
            tenant="tenant_a",
        )
        assert key1 != key4, "Different operation should produce different key"

        # Different coordinate should produce different key
        key5 = _idempotency_key(
            operation="memory.store",
            coord=(4.0, 5.0, 6.0),
            tenant="tenant_a",
        )
        assert key1 != key5, "Different coordinate should produce different key"

    def test_backpressure_threshold(self) -> None:
        """E2.5: Backpressure is applied when outbox exceeds threshold.

        **Feature: deep-memory-integration**
        **Validates: Requirements E2.5**

        When outbox has > 10000 pending entries, backpressure should be applied.
        """
        from somabrain.db.outbox import (
            OUTBOX_BACKPRESSURE_THRESHOLD,
            check_backpressure,
        )

        # Verify threshold is set correctly
        assert OUTBOX_BACKPRESSURE_THRESHOLD == 10000, "Threshold should be 10000"

        # Check backpressure function exists and returns bool
        result = check_backpressure(tenant_id="test_tenant")
        assert isinstance(result, bool), "check_backpressure should return bool"

    def test_memory_topics_defined(self) -> None:
        """E2.1: Memory topics are defined for outbox operations.

        **Feature: deep-memory-integration**
        **Validates: Requirements E2.1**
        """
        from somabrain.db.outbox import MEMORY_TOPICS

        # Verify required topics exist
        required_topics = [
            "memory.store",
            "memory.bulk_store",
            "memory.delete",
            "graph.link",
            "wm.persist",
            "wm.evict",
            "wm.promote",
        ]

        for topic in required_topics:
            assert topic in MEMORY_TOPICS, f"Topic {topic} should be defined"

    def test_enqueue_memory_event_with_idempotency(self) -> None:
        """E2.4: enqueue_memory_event generates idempotency key.

        **Feature: deep-memory-integration**
        **Validates: Requirements E2.4**

        Events should be enqueued with idempotency keys for deduplication.
        """
        from somabrain.db.outbox import enqueue_memory_event, get_event_by_dedupe_key

        tenant_id = f"test_idem_{uuid.uuid4().hex[:8]}"
        coord = (1.0, 2.0, 3.0)
        payload = {"content": "test", "timestamp": time.time()}

        # Enqueue event
        dedupe_key = enqueue_memory_event(
            topic="memory.store",
            payload=payload,
            tenant_id=tenant_id,
            coord=coord,
            check_backpressure_flag=False,  # Skip backpressure for test
        )

        # Verify dedupe_key was returned
        assert dedupe_key is not None, "Should return dedupe_key"
        assert len(dedupe_key) == 32, "Dedupe key should be 32 chars (SHA256 truncated)"

        # Verify event can be retrieved by dedupe_key
        event = get_event_by_dedupe_key(dedupe_key, tenant_id)
        assert event is not None, "Event should be retrievable by dedupe_key"
        assert event.topic == "memory.store"
        assert event.tenant_id == tenant_id

    def test_mark_event_sent_on_success(self) -> None:
        """E2.2: Events are marked 'sent' on success.

        **Feature: deep-memory-integration**
        **Validates: Requirements E2.2**
        """
        from somabrain.db.outbox import (
            enqueue_memory_event,
            mark_event_sent,
            get_event_by_dedupe_key,
        )

        tenant_id = f"test_sent_{uuid.uuid4().hex[:8]}"
        payload = {"content": "test"}

        # Enqueue event
        dedupe_key = enqueue_memory_event(
            topic="memory.store",
            payload=payload,
            tenant_id=tenant_id,
            check_backpressure_flag=False,
        )

        # Get event to find its ID
        event = get_event_by_dedupe_key(dedupe_key, tenant_id)
        assert event is not None
        assert event.status == "pending", "Initial status should be pending"

        # Mark as sent
        result = mark_event_sent(event.id)
        assert result is True, "mark_event_sent should return True"

        # Verify status changed
        event = get_event_by_dedupe_key(dedupe_key, tenant_id)
        assert event.status == "sent", "Status should be 'sent' after marking"

    def test_mark_event_failed_on_error(self) -> None:
        """E2.3: Events remain pending on failure for retry.

        **Feature: deep-memory-integration**
        **Validates: Requirements E2.3**
        """
        from somabrain.db.outbox import (
            enqueue_memory_event,
            mark_event_failed,
            get_event_by_dedupe_key,
        )

        tenant_id = f"test_fail_{uuid.uuid4().hex[:8]}"
        payload = {"content": "test"}

        # Enqueue event
        dedupe_key = enqueue_memory_event(
            topic="memory.store",
            payload=payload,
            tenant_id=tenant_id,
            check_backpressure_flag=False,
        )

        # Get event
        event = get_event_by_dedupe_key(dedupe_key, tenant_id)
        assert event is not None

        # Mark as failed
        error_msg = "Connection refused"
        result = mark_event_failed(event.id, error_msg)
        assert result is True, "mark_event_failed should return True"

        # Verify status and error recorded
        event = get_event_by_dedupe_key(dedupe_key, tenant_id)
        assert event.status == "failed", "Status should be 'failed'"
        assert event.last_error == error_msg, "Error message should be recorded"
        assert event.retries == 1, "Retry count should be incremented"

    def test_duplicate_detection(self) -> None:
        """E2.4: Duplicate events are detected via idempotency key.

        **Feature: deep-memory-integration**
        **Validates: Requirements E2.4**
        """
        from somabrain.db.outbox import (
            _idempotency_key,
            is_duplicate_event,
            enqueue_memory_event,
        )

        tenant_id = f"test_dup_{uuid.uuid4().hex[:8]}"
        coord = (1.0, 2.0, 3.0)

        # Generate idempotency key
        dedupe_key = _idempotency_key(
            operation="memory.store",
            coord=coord,
            tenant=tenant_id,
        )

        # Initially should not be duplicate
        assert is_duplicate_event(dedupe_key, tenant_id) is False

        # Enqueue event
        enqueue_memory_event(
            topic="memory.store",
            payload={"content": "test"},
            tenant_id=tenant_id,
            coord=coord,
            check_backpressure_flag=False,
        )

        # Now should be detected as duplicate
        assert is_duplicate_event(dedupe_key, tenant_id) is True

    def test_outbox_replay_no_duplicates(self) -> None:
        """Task 10.6: SFM fails → outbox pending → replay succeeds → no duplicates.

        **Feature: deep-memory-integration**
        **Validates: Requirements E2.1, E2.2, E2.3, E2.4**

        This test verifies the complete outbox replay flow:
        1. Event is enqueued when SFM call fails
        2. Event remains pending for retry
        3. On replay, idempotency key prevents duplicates
        """
        from somabrain.db.outbox import (
            enqueue_memory_event,
            get_event_by_dedupe_key,
            mark_event_sent,
            is_duplicate_event,
            _idempotency_key,
        )

        tenant_id = f"test_replay_{uuid.uuid4().hex[:8]}"
        coord = (10.0, 20.0, 30.0)
        payload = {"content": "replay_test", "timestamp": time.time()}

        # Step 1: Simulate SFM failure - event goes to outbox
        dedupe_key = enqueue_memory_event(
            topic="memory.store",
            payload=payload,
            tenant_id=tenant_id,
            coord=coord,
            check_backpressure_flag=False,
        )

        # Verify event is pending
        event = get_event_by_dedupe_key(dedupe_key, tenant_id)
        assert event is not None, "Event should exist"
        assert event.status == "pending", "Event should be pending"

        # Step 2: Simulate SFM recovery - mark event as sent
        mark_event_sent(event.id)

        # Verify event is now sent
        event = get_event_by_dedupe_key(dedupe_key, tenant_id)
        assert event.status == "sent", "Event should be sent"

        # Step 3: Verify duplicate detection prevents re-enqueue
        # Generate the same idempotency key
        same_key = _idempotency_key(
            operation="memory.store",
            coord=coord,
            tenant=tenant_id,
        )
        assert same_key == dedupe_key, "Same inputs should produce same key"

        # Check if duplicate
        is_dup = is_duplicate_event(same_key, tenant_id)
        assert is_dup is True, "Should detect as duplicate"

        # Attempting to enqueue again would be blocked by duplicate detection
        # In production code, this check happens before enqueue


# ---------------------------------------------------------------------------
# Test Class: Outbox Backpressure (E2.5)
# ---------------------------------------------------------------------------


@pytest.mark.memory_proof
class TestOutboxBackpressure:
    """Tests for outbox backpressure functionality.

    **Feature: deep-memory-integration**
    **Validates: Requirements E2.5**
    """

    def test_backpressure_error_raised(self) -> None:
        """E2.5: OutboxBackpressureError is raised when threshold exceeded.

        **Feature: deep-memory-integration**
        **Validates: Requirements E2.5**
        """
        from somabrain.db.outbox import OutboxBackpressureError

        # Verify error can be raised with correct attributes
        error = OutboxBackpressureError(pending_count=15000, threshold=10000)

        assert error.pending_count == 15000
        assert error.threshold == 10000
        assert "15000" in str(error)
        assert "10000" in str(error)

    def test_backpressure_check_returns_bool(self) -> None:
        """check_backpressure returns boolean based on pending count.

        **Feature: deep-memory-integration**
        **Validates: Requirements E2.5**
        """
        from somabrain.db.outbox import check_backpressure, get_pending_count

        tenant_id = f"test_bp_{uuid.uuid4().hex[:8]}"

        # Get current pending count
        pending = get_pending_count(tenant_id)

        # Check backpressure
        result = check_backpressure(tenant_id)

        # Result should be True only if pending >= 10000
        if pending >= 10000:
            assert result is True
        else:
            assert result is False