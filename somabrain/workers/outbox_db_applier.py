"""
Outbox DB Applier

Consumes pending outbox_events with topic 'memory.episodic.snapshot' and persists
their payload into the episodic_snapshots table, then marks the outbox event as sent.

This enables DB persistence even without Kafka, while the outbox_publisher can be
used to stream the same payloads to Kafka if desired.
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict

from sqlalchemy.orm import Session

from somabrain.db.models.outbox import OutboxEvent
from somabrain.db.models.episodic import EpisodicSnapshot
from somabrain.storage.db import get_session_factory


TOPIC = "memory.episodic.snapshot"


def _apply_event(session: Session, ev: OutboxEvent) -> None:
    payload: Dict[str, Any] = ev.payload or {}
    tenant = (payload.get("tenant") or ev.tenant_id or None)
    namespace = payload.get("namespace")
    key = payload.get("key") or ""
    value = payload.get("value") or {}
    tags = payload.get("tags") or None
    policy_tags = payload.get("policy_tags") or None
    snap = EpisodicSnapshot(
        tenant_id=str(tenant) if tenant else None,
        namespace=str(namespace) if namespace else None,
        key=str(key),
        value=value,
        tags=tags,
        policy_tags=policy_tags,
    )
    session.add(snap)
    ev.status = "sent"
    session.add(ev)


def run_forever() -> None:  # pragma: no cover - integration loop
    poll_interval = float(os.getenv("SOMABRAIN_OUTBOX_POLL_INTERVAL", "1.0") or 1.0)
    batch_size = int(os.getenv("SOMABRAIN_OUTBOX_BATCH_SIZE", "100") or 100)
    session_factory = get_session_factory()
    while True:
        with session_factory() as session:
            events = (
                session.query(OutboxEvent)
                .filter(OutboxEvent.status == "pending", OutboxEvent.topic == TOPIC)
                .order_by(OutboxEvent.created_at)
                .limit(batch_size)
                .all()
            )
            if not events:
                time.sleep(poll_interval)
                continue
            for ev in events:
                try:
                    _apply_event(session, ev)
                except Exception as e:
                    ev.retries = int(ev.retries or 0) + 1
                    ev.last_error = str(e)
                    if ev.retries >= int(os.getenv("SOMABRAIN_OUTBOX_MAX_RETRIES", "5") or 5):
                        ev.status = "failed"
                    session.add(ev)
            session.commit()


def main() -> None:  # pragma: no cover
    run_forever()


if __name__ == "__main__":  # pragma: no cover
    main()
