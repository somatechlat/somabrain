"""
API for interacting with the transactional outbox.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from somabrain.db.models.outbox import OutboxEvent
from somabrain.storage.db import get_session_factory


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
    If tenant_id is provided, filter events for that tenant.
    """
    session_factory = get_session_factory()
    with session_factory() as session:
        query = session.query(OutboxEvent).filter(OutboxEvent.status == "pending")
        
        if tenant_id:
            query = query.filter(OutboxEvent.tenant_id == tenant_id)
            
        events = (
            query.order_by(OutboxEvent.created_at)
            .limit(limit)
            .all()
        )
        return events
