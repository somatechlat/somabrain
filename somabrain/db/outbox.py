"""
API for interacting with the transactional outbox.

Per Requirements E2.1-E2.5:
- E2.1: remember() records to outbox before SFM call
- E2.2: Mark "sent" on success
- E2.3: Remain "pending" on failure for retry
- E2.4: Duplicate detection via idempotency key
- E2.5: Backpressure when outbox > 10000 entries
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func

from somabrain.db.models.outbox import OutboxEvent
from somabrain.storage.db import get_session_factory
from somabrain.metrics import report_outbox_replayed
from somabrain.journal import get_journal, JournalEvent

logger = logging.getLogger(__name__)

VALID_OUTBOX_STATUSES = {"pending", "sent", "failed"}

# Memory operation topics per Task 10.1
MEMORY_TOPICS: Dict[str, str] = {
    "memory.store": "Store memory to SFM",
    "memory.bulk_store": "Bulk store memories to SFM",
    "memory.delete": "Delete memory from SFM",
    "graph.link": "Create graph link in SFM",
    "graph.delete_link": "Delete graph link in SFM",
    "wm.persist": "Persist WM item to SFM",
    "wm.evict": "Mark WM item as evicted in SFM",
    "wm.promote": "Promote WM item to LTM",
}

# Backpressure threshold per E2.5
OUTBOX_BACKPRESSURE_THRESHOLD = 10000


class OutboxBackpressureError(Exception):
    """Raised when outbox exceeds backpressure threshold.

    Per Requirement E2.5: Backpressure when outbox > 10000 entries.
    """

    def __init__(self, pending_count: int, threshold: int = OUTBOX_BACKPRESSURE_THRESHOLD):
        self.pending_count = pending_count
        self.threshold = threshold
        super().__init__(
            f"Outbox backpressure: {pending_count} pending events exceeds threshold {threshold}"
        )


def _idempotency_key(
    operation: str,
    coord: Optional[Tuple[float, float, float]] = None,
    tenant: str = "default",
    extra: Optional[str] = None,
) -> str:
    """Generate idempotency key for deduplication.

    Per Requirement E2.4: Duplicate detection via idempotency key.

    Args:
        operation: The operation type (e.g., "memory.store", "graph.link")
        coord: Optional coordinate tuple for memory operations
        tenant: Tenant ID for scoping
        extra: Optional extra data to include in key (e.g., link_type)

    Returns:
        32-character hex string idempotency key
    """
    parts = [operation, tenant]
    if coord is not None:
        parts.append(f"{coord[0]:.6f},{coord[1]:.6f},{coord[2]:.6f}")
    if extra:
        parts.append(extra)
    data = ":".join(parts)
    return hashlib.sha256(data.encode()).hexdigest()[:32]


def check_backpressure(tenant_id: Optional[str] = None) -> bool:
    """Check if outbox is under backpressure.

    Per Requirement E2.5: Returns True if pending count exceeds threshold.

    Args:
        tenant_id: Optional tenant to check (None checks global)

    Returns:
        True if backpressure should be applied
    """
    pending = get_pending_count(tenant_id=tenant_id)
    return pending >= OUTBOX_BACKPRESSURE_THRESHOLD


def enqueue_memory_event(
    topic: str,
    payload: Dict[str, Any],
    tenant_id: str,
    coord: Optional[Tuple[float, float, float]] = None,
    extra_key: Optional[str] = None,
    session: Optional[Session] = None,
    check_backpressure_flag: bool = True,
) -> str:
    """Enqueue a memory operation event with idempotency key.

    Per Requirements E2.1-E2.5:
    - Generates idempotency key for deduplication
    - Checks backpressure before enqueueing
    - Returns the dedupe_key for tracking

    Args:
        topic: Event topic (must be in MEMORY_TOPICS)
        payload: Event payload data
        tenant_id: Tenant identifier
        coord: Optional coordinate for idempotency key
        extra_key: Optional extra data for idempotency key
        session: Optional database session
        check_backpressure_flag: Whether to check backpressure (default True)

    Returns:
        The dedupe_key used for this event

    Raises:
        OutboxBackpressureError: If backpressure threshold exceeded
        ValueError: If topic is not a valid memory topic
    """
    if topic not in MEMORY_TOPICS:
        logger.warning(f"Unknown memory topic: {topic}, proceeding anyway")

    # Check backpressure per E2.5
    if check_backpressure_flag and check_backpressure(tenant_id):
        pending = get_pending_count(tenant_id)
        raise OutboxBackpressureError(pending)

    # Generate idempotency key per E2.4
    dedupe_key = _idempotency_key(
        operation=topic,
        coord=coord,
        tenant=tenant_id,
        extra=extra_key,
    )

    # Enqueue the event
    enqueue_event(
        topic=topic,
        payload=payload,
        dedupe_key=dedupe_key,
        tenant_id=tenant_id,
        session=session,
    )

    logger.debug(
        f"Enqueued memory event: topic={topic}, tenant={tenant_id}, dedupe_key={dedupe_key}"
    )

    return dedupe_key


def mark_event_sent(event_id: int, session: Optional[Session] = None) -> bool:
    """Mark an outbox event as sent.

    Per Requirement E2.2: Mark "sent" on success.

    Args:
        event_id: The event ID to mark
        session: Optional database session

    Returns:
        True if event was marked, False if not found
    """
    session_factory = get_session_factory()

    if session is None:
        with session_factory() as session:
            event = session.query(OutboxEvent).filter(OutboxEvent.id == event_id).first()
            if event:
                event.status = "sent"
                session.commit()
                return True
            return False
    else:
        event = session.query(OutboxEvent).filter(OutboxEvent.id == event_id).first()
        if event:
            event.status = "sent"
            return True
        return False


def mark_event_failed(
    event_id: int,
    error: str,
    session: Optional[Session] = None,
) -> bool:
    """Mark an outbox event as failed with error message.

    Per Requirement E2.3: Remain "pending" for retry, but track failures.

    Args:
        event_id: The event ID to mark
        error: Error message to record
        session: Optional database session

    Returns:
        True if event was marked, False if not found
    """
    session_factory = get_session_factory()

    if session is None:
        with session_factory() as session:
            event = session.query(OutboxEvent).filter(OutboxEvent.id == event_id).first()
            if event:
                event.status = "failed"
                event.last_error = error[:1000] if error else None  # Truncate long errors
                event.retries = (event.retries or 0) + 1
                session.commit()
                return True
            return False
    else:
        event = session.query(OutboxEvent).filter(OutboxEvent.id == event_id).first()
        if event:
            event.status = "failed"
            event.last_error = error[:1000] if error else None
            event.retries = (event.retries or 0) + 1
            return True
        return False


def get_event_by_dedupe_key(
    dedupe_key: str,
    tenant_id: Optional[str] = None,
) -> Optional[OutboxEvent]:
    """Get an outbox event by its deduplication key.

    Per Requirement E2.4: Used for duplicate detection.

    Args:
        dedupe_key: The deduplication key to search for
        tenant_id: Optional tenant to scope the search

    Returns:
        OutboxEvent if found, None otherwise
    """
    session_factory = get_session_factory()
    with session_factory() as session:
        q = session.query(OutboxEvent).filter(OutboxEvent.dedupe_key == dedupe_key)
        if tenant_id:
            q = q.filter(OutboxEvent.tenant_id == tenant_id)
        return q.first()


def is_duplicate_event(
    dedupe_key: str,
    tenant_id: Optional[str] = None,
) -> bool:
    """Check if an event with this dedupe_key already exists.

    Per Requirement E2.4: Duplicate detection.

    Args:
        dedupe_key: The deduplication key to check
        tenant_id: Optional tenant to scope the check

    Returns:
        True if event already exists
    """
    return get_event_by_dedupe_key(dedupe_key, tenant_id) is not None


def enqueue_event(
    topic: str,
    payload: Dict[str, Any],
    dedupe_key: Optional[str] = None,
    tenant_id: Optional[str] = None,
    session: Optional[Session] = None,
) -> None:
    """
    Enqueue a new event to the outbox.

    Args:
        topic: Event topic
        payload: Event payload data
        dedupe_key: Optional deduplication key
        tenant_id: Optional tenant identifier
        session: Optional database session
    """
    if dedupe_key is None:
        dedupe_key = str(uuid.uuid4())

    event = OutboxEvent(
        topic=topic,
        payload=payload,
        dedupe_key=dedupe_key,
        tenant_id=tenant_id,
    )

    if session is None:
        session_factory = get_session_factory()
        with session_factory() as session:
            session.add(event)
            session.commit()
    else:
        session.add(event)

    # Write to journal for redundancy and durability
    journal = get_journal()
    journal_event = JournalEvent(
        id=event.id,
        topic=topic,
        payload=payload,
        tenant_id=tenant_id,
        dedupe_key=dedupe_key,
        status="pending",
    )
    journal.append_event(journal_event)


def get_pending_events(limit: int = 100, tenant_id: Optional[str] = None) -> List[OutboxEvent]:
    """
    Fetch a batch of pending events from the outbox.

    If `tenant_id` is provided, only events for that tenant are returned.
    Uses the optimized index `ix_outbox_status_tenant_created` for efficient queries.
    """
    session_factory = get_session_factory()
    with session_factory() as session:
        q = session.query(OutboxEvent).filter(OutboxEvent.status == "pending")
        if tenant_id:
            q = q.filter(OutboxEvent.tenant_id == tenant_id)
        # Order by created_at to ensure FIFO processing
        events = q.order_by(OutboxEvent.created_at).limit(limit).all()
        return events


def list_events_by_status(
    status: str = "pending",
    tenant_id: Optional[str] = None,
    topic_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[OutboxEvent]:
    """
    List outbox events by status with filtering options.

    This function provides comprehensive filtering for admin endpoints,
    supporting status-based queries with optional tenant and topic filtering.

    Args:
        status: Event status to filter by (pending, failed, sent)
        tenant_id: Optional tenant ID to filter events
        topic_filter: Optional topic pattern to filter events
        limit: Maximum number of events to return
        offset: Offset for pagination

    Returns:
        List of OutboxEvent objects matching the criteria

    Raises:
        ValueError: If status is not valid
    """
    if status not in VALID_OUTBOX_STATUSES:
        raise ValueError(f"Invalid outbox status: {status}")

    limit = max(1, min(int(limit), 500))
    offset = max(0, int(offset))

    session_factory = get_session_factory()
    with session_factory() as session:
        q = session.query(OutboxEvent).filter(OutboxEvent.status == status)

        if tenant_id:
            q = q.filter(OutboxEvent.tenant_id == tenant_id)

        if topic_filter:
            q = q.filter(OutboxEvent.topic.like(f"%{topic_filter}%"))

        events = q.order_by(OutboxEvent.created_at.desc()).offset(offset).limit(limit).all()
        return events


def get_pending_events_by_tenant_batch(
    limit_per_tenant: int = 50, max_tenants: Optional[int] = None
) -> Dict[str, List[OutboxEvent]]:
    """
    Fetch pending events grouped by tenant, with configurable limits.

    This function enables per-tenant batch processing for the outbox worker,
    preventing any single tenant from dominating the processing queue.

    Args:
        limit_per_tenant: Maximum number of events to fetch per tenant
        max_tenants: Maximum number of tenants to process (None for all)

    Returns:
        Dict mapping tenant_id to list of pending events for that tenant
    """
    session_factory = get_session_factory()
    with session_factory() as session:
        # First, get all tenants with pending events
        tenant_query = (
            session.query(OutboxEvent.tenant_id).filter(OutboxEvent.status == "pending").distinct()
        )

        if max_tenants:
            tenant_query = tenant_query.limit(max_tenants)

        tenants = [row[0] for row in tenant_query.all() if row[0] is not None]

        # If no tenants found, check for NULL tenant_id events
        if not tenants:
            null_count = (
                session.query(func.count(OutboxEvent.id))
                .filter(OutboxEvent.status == "pending")
                .filter(OutboxEvent.tenant_id.is_(None))
                .scalar()
            )
            if null_count > 0:
                tenants = [None]

        # Fetch events for each tenant
        results = {}
        for tenant_id in tenants:
            events = (
                session.query(OutboxEvent)
                .filter(OutboxEvent.status == "pending")
                .filter(OutboxEvent.tenant_id == tenant_id)
                .order_by(OutboxEvent.created_at)
                .limit(limit_per_tenant)
                .all()
            )
            if events:
                tenant_label = tenant_id or "default"
                results[tenant_label] = events

        return results


def get_pending_count(tenant_id: Optional[str] = None) -> int:
    """
    Return the number of pending outbox events. If `tenant_id` is provided,
    the count is restricted to that tenant.
    """
    session_factory = get_session_factory()
    with session_factory() as session:
        q = session.query(func.count(OutboxEvent.id)).filter(OutboxEvent.status == "pending")
        if tenant_id:
            q = q.filter(OutboxEvent.tenant_id == tenant_id)
        count = q.scalar() or 0
        return int(count)


def get_pending_counts_by_tenant() -> dict[str, int]:
    """
    Return the current pending event count per tenant.
    """
    session_factory = get_session_factory()
    with session_factory() as session:
        rows = (
            session.query(OutboxEvent.tenant_id, func.count(OutboxEvent.id))
            .filter(OutboxEvent.status == "pending")
            .group_by(OutboxEvent.tenant_id)
            .all()
        )
        return {tenant or "default": int(cnt) for tenant, cnt in rows}


# Replay functions - Extracted to somabrain/db/outbox_replay.py
# Re-export for backward compatibility
from somabrain.db.outbox_replay import (
    mark_events_for_replay,
    mark_tenant_events_for_replay,
    list_tenant_events,
    get_failed_counts_by_tenant,
    get_sent_counts_by_tenant,
)


# Journal Integration Functions - Extracted to somabrain/db/outbox_journal.py
# Re-export for backward compatibility
from somabrain.db.outbox_journal import (
    get_journal_events,
    replay_journal_events,
    get_journal_stats,
    cleanup_journal,
)
