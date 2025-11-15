"""
API for interacting with the transactional outbox.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy.orm import Session
from sqlalchemy import func

from somabrain.db.models.outbox import OutboxEvent
from somabrain.storage.db import get_session_factory
try:  # metrics optional
    from somabrain.metrics import report_outbox_replayed
except Exception:  # pragma: no cover
    report_outbox_replayed = None

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


def get_pending_events(limit: int = 100, tenant_id: Optional[str] = None) -> List[OutboxEvent]:
    """
    Fetch a batch of pending events from the outbox.

    If `tenant_id` is provided, only events for that tenant are returned.
    """
    session_factory = get_session_factory()
    with session_factory() as session:
        q = session.query(OutboxEvent).filter(OutboxEvent.status == "pending")
        if tenant_id:
            q = q.filter(OutboxEvent.tenant_id == tenant_id)
        events = q.order_by(OutboxEvent.created_at).limit(limit).all()
        return events


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


def list_events_by_status(
    status: str,
    tenant_id: Optional[str] = None,
    *,
    limit: int = 100,
    offset: int = 0,
) -> List[OutboxEvent]:
    """Return events matching *status* (pending|failed|sent) for inspection."""
    if status not in VALID_OUTBOX_STATUSES:
        raise ValueError(f"Unsupported outbox status: {status}")
    limit = max(1, min(int(limit or 1), 1000))
    offset = max(0, int(offset or 0))
    session_factory = get_session_factory()
    with session_factory() as session:
        q = session.query(OutboxEvent).filter(OutboxEvent.status == status)
        if tenant_id:
            q = q.filter(OutboxEvent.tenant_id == tenant_id)
        events = (
            q.order_by(OutboxEvent.created_at, OutboxEvent.id)
            .offset(offset)
            .limit(limit)
            .all()
        )
        return events


def mark_events_for_replay(event_ids: Sequence[int]) -> int:
    """Reset events to pending status so the outbox worker reprocesses them."""
    ids = [int(eid) for eid in event_ids if eid is not None]
    if not ids:
        return 0
    session_factory = get_session_factory()
    with session_factory() as session:
        rows = (
            session.query(OutboxEvent)
            .filter(OutboxEvent.id.in_(ids))
            .with_for_update()
            .all()
        )
        count = 0
        per_tenant: Dict[str, int] = {}
        for ev in rows:
            ev.status = "pending"
            ev.retries = 0
            ev.last_error = None
            tenant_label = ev.tenant_id or "default"
            per_tenant[tenant_label] = per_tenant.get(tenant_label, 0) + 1
            count += 1
        session.commit()
        if report_outbox_replayed is not None:
            for tenant_label, n in per_tenant.items():
                try:
                    report_outbox_replayed(tenant_label, n)
                except Exception:
                    continue
        return count
