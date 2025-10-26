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
try:
    from somabrain import metrics as _metrics  # type: ignore
except Exception:  # pragma: no cover
    _metrics = None  # type: ignore


TOPIC = "memory.episodic.snapshot"

# Metrics (lazy-resolved to avoid hard dependency at import time)
_APPLIED = None
_ERRORS = None
_LAT_E2E = None


def _init_metrics() -> None:
    global _APPLIED, _ERRORS, _LAT_E2E
    if _metrics is None:
        return
    if _APPLIED is None:
        try:
            _APPLIED = _metrics.get_counter(
                "somabrain_outbox_applier_applied_total",
                "Outbox events applied to DB",
                labelnames=["topic"],
            )
        except Exception:
            _APPLIED = None
    if _ERRORS is None:
        try:
            _ERRORS = _metrics.get_counter(
                "somabrain_outbox_applier_errors_total",
                "Errors applying outbox events",
                labelnames=["topic"],
            )
        except Exception:
            _ERRORS = None
    if _LAT_E2E is None:
        try:
            _LAT_E2E = _metrics.get_histogram(
                "somabrain_outbox_event_e2e_seconds",
                "End-to-end latency from outbox enqueue to DB apply",
                labelnames=["topic"],
                buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
            )
        except Exception:
            _LAT_E2E = None


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
    # Observe e2e latency based on outbox created_at timestamp
    try:
        if _LAT_E2E is not None and getattr(ev, "created_at", None) is not None:
            now = time.time()
            # created_at may be datetime; convert to seconds
            ca = ev.created_at
            t0 = getattr(ca, "timestamp", None)
            if callable(t0):
                t0s = float(t0())
            else:
                # if already a float
                t0s = float(ca)
            _LAT_E2E.labels(topic=ev.topic or "").observe(max(0.0, now - t0s))
    except Exception:
        pass


def run_forever() -> None:  # pragma: no cover - integration loop
    _init_metrics()
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
                    try:
                        if _APPLIED is not None:
                            _APPLIED.labels(topic=ev.topic or "").inc()
                    except Exception:
                        pass
                except Exception as e:
                    ev.retries = int(ev.retries or 0) + 1
                    ev.last_error = str(e)
                    if ev.retries >= int(os.getenv("SOMABRAIN_OUTBOX_MAX_RETRIES", "5") or 5):
                        ev.status = "failed"
                    session.add(ev)
                    try:
                        if _ERRORS is not None:
                            _ERRORS.labels(topic=ev.topic or "").inc()
                    except Exception:
                        pass
            session.commit()


def main() -> None:  # pragma: no cover
    run_forever()


if __name__ == "__main__":  # pragma: no cover
    main()
