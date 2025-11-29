"""
API for interacting with the transactional outbox.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from somabrain.db.models.outbox import OutboxEvent
from somabrain.storage.db import get_session_factory
from somabrain.metrics import report_outbox_replayed
from somabrain.journal import get_journal, JournalEvent

VALID_OUTBOX_STATUSES = {"pending", "sent", "failed"}


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


def get_pending_events(
    limit: int = 100, tenant_id: Optional[str] = None
) -> List[OutboxEvent]:
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
            session.query(OutboxEvent.tenant_id)
            .filter(OutboxEvent.status == "pending")
            .distinct()
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
        q = session.query(func.count(OutboxEvent.id)).filter(
            OutboxEvent.status == "pending"
        )
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


def mark_events_for_replay(limit: int = 100, tenant_id: Optional[str] = None) -> int:
    """
    Mark failed events for replay by setting their status back to 'pending'.

    Args:
        limit: Maximum number of events to mark for replay
        tenant_id: Specific tenant to replay (None for all tenants)

    Returns:
        Number of events marked for replay
    """
    session_factory = get_session_factory()
    with session_factory() as session:
        q = session.query(OutboxEvent).filter(OutboxEvent.status == "failed")
        if tenant_id:
            q = q.filter(OutboxEvent.tenant_id == tenant_id)

        events = q.order_by(OutboxEvent.created_at).limit(limit).all()
        count = 0

        for ev in events:
            ev.status = "pending"
            ev.retries = 0
            ev.last_error = None
            count += 1

        session.commit()

        # Report metrics
        tenant_label = tenant_id or "default"
        if report_outbox_replayed is not None and count > 0:
            try:
                report_outbox_replayed(tenant_label, count)
            except Exception as exc: raise

        return count


def mark_tenant_events_for_replay(
    tenant_id: str, limit: int = 100, status: str = "failed"
) -> int:
    """
    Mark events for a specific tenant for replay.

    Args:
        tenant_id: The tenant ID to replay events for
        limit: Maximum number of events to replay
        status: Status of events to replay (failed or sent)

    Returns:
        Number of events marked for replay
    """
    if status not in VALID_OUTBOX_STATUSES:
        raise ValueError(f"Invalid outbox status: {status}")

    limit = max(1, min(int(limit), 1000))

    session_factory = get_session_factory()
    with session_factory() as session:
        events = (
            session.query(OutboxEvent)
            .filter(OutboxEvent.tenant_id == tenant_id)
            .filter(OutboxEvent.status == status)
            .order_by(OutboxEvent.created_at)
            .limit(limit)
            .all()
        )

        count = 0
        for ev in events:
            ev.status = "pending"
            ev.retries = 0
            ev.last_error = None
            count += 1

        session.commit()

        # Report metrics
        if report_outbox_replayed is not None and count > 0:
            try:
                report_outbox_replayed(tenant_id, count)
            except Exception as exc: raise

        return count


def list_tenant_events(
    tenant_id: str,
    status: str = "pending",
    topic_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[OutboxEvent]:
    """List outbox events for a specific tenant with filtering options.

    Args:
        tenant_id: The tenant ID to get events for
        status: Filter events by status (pending|failed|sent)
        topic_filter: Optional topic pattern to filter events
        limit: Maximum number of events to return
        offset: Offset for pagination

    Returns:
        List of outbox events
    """
    if status not in VALID_OUTBOX_STATUSES:
        raise ValueError(f"Invalid outbox status: {status}")

    limit = max(1, min(int(limit), 1000))
    offset = max(0, int(offset))

    session_factory = get_session_factory()
    with session_factory() as session:
        query = session.query(OutboxEvent).filter(OutboxEvent.tenant_id == tenant_id)

        # Apply status filter
        query = query.filter(OutboxEvent.status == status)

        # Apply topic filter if provided
        if topic_filter:
            query = query.filter(OutboxEvent.topic.like(f"%{topic_filter}%"))

        # Apply pagination
        events = (
            query.order_by(OutboxEvent.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return events


def get_failed_counts_by_tenant() -> Dict[str, int]:
    """Get failed event counts per tenant.

    Returns:
        Dict mapping tenant_id to failed event count
    """
    session_factory = get_session_factory()
    with session_factory() as session:
        rows = (
            session.query(OutboxEvent.tenant_id, func.count(OutboxEvent.id))
            .filter(OutboxEvent.status == "failed")
            .group_by(OutboxEvent.tenant_id)
            .all()
        )
        return {tenant or "default": int(cnt) for tenant, cnt in rows}


def get_sent_counts_by_tenant() -> Dict[str, int]:
    """Get sent event counts per tenant.

    Returns:
        Dict mapping tenant_id to sent event count
    """
    session_factory = get_session_factory()
    with session_factory() as session:
        rows = (
            session.query(OutboxEvent.tenant_id, func.count(OutboxEvent.id))
            .filter(OutboxEvent.status == "sent")
            .group_by(OutboxEvent.tenant_id)
            .all()
        )
        return {tenant or "default": int(cnt) for tenant, cnt in rows}


# Journal Integration Functions


def get_journal_events(
    tenant_id: Optional[str] = None,
    status: Optional[str] = None,
    topic: Optional[str] = None,
    limit: Optional[int] = None,
    since: Optional[datetime] = None,
) -> List[JournalEvent]:
    """Get events from the local journal with filtering.

    Args:
        tenant_id: Optional tenant ID to filter by
        status: Optional status to filter by (pending|sent|failed)
        topic: Optional topic to filter by
        limit: Maximum number of events to return
        since: Only return events after this datetime

    Returns:
        List of journal events
    """
    try:
        journal = get_journal()
        return journal.read_events(
            tenant_id=tenant_id, status=status, topic=topic, limit=limit, since=since
        )
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Failed to read from journal: {e}")
        return []


def replay_journal_events(
    tenant_id: Optional[str] = None,
    limit: int = 100,
    mark_processed: bool = True,
) -> int:
    """Replay journal events to the database outbox.

    This function reads events from the local journal and enqueues them
    in the database outbox for processing by the outbox worker.

    Args:
        tenant_id: Optional tenant ID to filter events
        limit: Maximum number of events to replay
        mark_processed: Whether to mark replayed events as processed in journal

    Returns:
        Number of events successfully replayed
    """
    journal = get_journal()

    # Get pending events from journal
    events = journal.read_events(tenant_id=tenant_id, status="pending", limit=limit)

    if not events:
        return 0

    replayed_count = 0
    event_ids = []

    # Replay events to database outbox
    for event in events:
        try:
            enqueue_event(
                topic=event.topic,
                payload=event.payload,
                dedupe_key=event.dedupe_key,
                tenant_id=event.tenant_id,
            )
            replayed_count += 1
            event_ids.append(event.id)

        except Exception as e:
            import logging

            logging.getLogger(__name__).error(
                f"Failed to replay journal event {event.id} to database: {e}"
            )
            continue

    # Mark replayed events as processed in journal
    if mark_processed and event_ids:
        try:
            journal.mark_events_sent(event_ids)
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(
                f"Failed to mark journal events as processed: {e}"
            )

    return replayed_count


def get_journal_stats() -> Dict[str, Any]:
    """Get statistics about the local journal.

    Returns:
        Dictionary with journal statistics
    """
    try:
        journal = get_journal()
        return journal.get_stats()
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Failed to get journal stats: {e}")
        return {"error": str(e)}


def cleanup_journal() -> Dict[str, Any]:
    """Clean up the local journal by removing old files.

    Returns:
        Dictionary with cleanup results
    """
    try:
        journal = get_journal()
        journal._cleanup_old_files()
        return {"success": True, "message": "Journal cleanup completed"}
    except Exception as e:
        import logging

        logging.getLogger(__name__).error(f"Failed to clean up journal: {e}")
        return {"success": False, "error": str(e)}
