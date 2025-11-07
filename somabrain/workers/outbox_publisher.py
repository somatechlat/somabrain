"""
Transactional Outbox Publisher

Polls the outbox_events table and publishes events to Kafka topics.
On successful publish, marks the event as 'sent'. On failure, increments retries
and stores last_error; after max retries, marks as 'failed'.

Environment:
- SOMABRAIN_KAFKA_URL: kafka://host:port
- SOMABRAIN_OUTBOX_BATCH_SIZE: default 100
- SOMABRAIN_OUTBOX_MAX_RETRIES: default 5
- SOMABRAIN_OUTBOX_POLL_INTERVAL: seconds between empty polls (default 1.0)
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional
import logging

from sqlalchemy.orm import Session

from somabrain.db.models.outbox import OutboxEvent
from somabrain.storage.db import get_session_factory


def _bootstrap() -> Optional[str]:
    url = os.getenv("SOMABRAIN_KAFKA_URL")
    if not url:
        return None
    return url.replace("kafka://", "").strip()


def _make_producer():  # pragma: no cover - optional at runtime
    bootstrap = _bootstrap()
    if not bootstrap:
        return None
    try:
        from kafka import KafkaProducer  # type: ignore

        return KafkaProducer(
            bootstrap_servers=bootstrap,
            acks="1",
            linger_ms=10,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
    except Exception:
        return None


def _publish_record(producer, topic: str, payload: Dict[str, Any]) -> None:
    if producer is None:
        raise RuntimeError("Kafka producer not available")
    producer.send(topic, value=payload)


def _process_batch(session: Session, producer, batch_size: int, max_retries: int) -> int:
    events = (
        session.query(OutboxEvent)
        .filter(OutboxEvent.status == "pending")
        .order_by(OutboxEvent.created_at)
        .limit(batch_size)
        .all()
    )
    if not events:
        return 0
    sent = 0
    for ev in events:
        try:
            _publish_record(producer, ev.topic, ev.payload)
            ev.status = "sent"
            sent += 1
        except Exception as e:
            ev.retries = int(ev.retries or 0) + 1
            ev.last_error = str(e)
            if ev.retries >= max_retries:
                ev.status = "failed"
        session.add(ev)
    session.commit()
    # Best-effort flush
    try:
        if producer is not None:
            producer.flush(2)
    except Exception:
        pass
    return sent


def run_forever() -> None:  # pragma: no cover - integration loop
    batch_size = int(os.getenv("SOMABRAIN_OUTBOX_BATCH_SIZE", "100") or 100)
    max_retries = int(os.getenv("SOMABRAIN_OUTBOX_MAX_RETRIES", "5") or 5)
    poll_interval = float(os.getenv("SOMABRAIN_OUTBOX_POLL_INTERVAL", "1.0") or 1.0)
    session_factory = get_session_factory()
    producer = _make_producer()
    if producer is None:
        logging.error("outbox_publisher: Kafka unavailable; exiting fail-fast")
        raise SystemExit(1)
    while True:
        with session_factory() as session:
            try:
                n = _process_batch(session, producer, batch_size, max_retries)
            except Exception as e:
                # Safety net: don't crash the loop on DB issues
                logging.error("outbox_publisher: batch error: %s", e)
                n = 0
        if n == 0:
            time.sleep(poll_interval)


def main() -> None:  # pragma: no cover
    run_forever()


if __name__ == "__main__":  # pragma: no cover
    main()
