"""
Replay functions for the transactional outbox.

Extracted from somabrain/db/outbox.py per vibe-compliance-audit spec.
Provides functions for replaying failed events and tenant-specific replay.

Thread Safety:
    Database operations use SQLAlchemy sessions which are not thread-safe.
    Each function creates its own session for thread safety.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from somabrain.db.models.outbox import OutboxEvent
from somabrain.storage.db import get_session_factory
from somabrain.metrics import report_outbox_replayed

logger = logging.getLogger(__name__)

VALID_OUTBOX_STATUSES = {"pending", "sent", "failed"}


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
            except Exception as exc:
                logger.debug(
                    "Failed to report outbox replayed for tenant=%s: %s",
                    tenant_label,
                    exc,
                )

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
            except Exception as exc:
                logger.debug(
                    "Failed to report outbox replayed for tenant=%s: %s", tenant_id, exc
                )

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
    from sqlalchemy import func

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
    from sqlalchemy import func

    session_factory = get_session_factory()
    with session_factory() as session:
        rows = (
            session.query(OutboxEvent.tenant_id, func.count(OutboxEvent.id))
            .filter(OutboxEvent.status == "sent")
            .group_by(OutboxEvent.tenant_id)
            .all()
        )
        return {tenant or "default": int(cnt) for tenant, cnt in rows}
