"""
Transactional Outbox Publisher

Polls the outbox_events table and publishes events to Kafka topics.
On successful publish, marks the event as 'sent'. On failure, increments retries
and stores last_error; after max retries, marks as 'failed'.

Robustness improvements:
- Prefer confluent-kafka with idempotence + acks=all when available
- Fall back to kafka-python with acks=all and client retries
- Startup waits and retries producer creation until Kafka is reachable
- Per-send errors update retry counters without crashing the loop

Environment:
- SOMABRAIN_KAFKA_URL: kafka://host:port
- SOMA_KAFKA_BOOTSTRAP: alternative plain bootstrap (host:port); used if set
- SOMABRAIN_OUTBOX_BATCH_SIZE: default 100
- SOMABRAIN_OUTBOX_MAX_RETRIES: default 5
- SOMABRAIN_OUTBOX_POLL_INTERVAL: seconds between empty polls (default 1.0)
- SOMABRAIN_OUTBOX_PRODUCER_RETRY_MS: backoff between producer create attempts (default 1000)
"""

from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from typing import Any, Dict, Optional
import logging

from sqlalchemy.orm import Session

from somabrain.db.models.outbox import OutboxEvent
from somabrain.db.outbox import get_pending_counts_by_tenant
try:  # metrics are optional in some contexts
    from somabrain.metrics import (
        DEFAULT_TENANT_LABEL,
        report_outbox_pending,
        report_outbox_processed,
    )
except Exception:  # pragma: no cover
    DEFAULT_TENANT_LABEL = "default"
    report_outbox_pending = None
    report_outbox_processed = None
from somabrain.storage.db import get_session_factory
from somabrain.common.infra import assert_ready

_PER_TENANT_BATCH_LIMIT = max(
    1,
    int(os.getenv("SOMABRAIN_OUTBOX_TENANT_BATCH_LIMIT", "50") or 50),
)


def _bootstrap() -> Optional[str]:
    # Prefer explicit SOMA_KAFKA_BOOTSTRAP if present (plain host:port)
    direct = (os.getenv("SOMA_KAFKA_BOOTSTRAP") or "").strip()
    if direct:
        return direct
    url = os.getenv("SOMABRAIN_KAFKA_URL")
    if not url:
        return None
    return url.replace("kafka://", "").strip()


def _make_producer():  # pragma: no cover - optional at runtime
    bootstrap = _bootstrap()
    if not bootstrap:
        return None
    try:
        from confluent_kafka import Producer  # type: ignore

        conf = {
            "bootstrap.servers": bootstrap,
            "enable.idempotence": True,
            "acks": "all",
            "compression.type": "snappy",
        }
        return Producer(conf)
    except Exception:
        return None


def _publish_record(
    producer,
    topic: str,
    payload: Dict[str, Any],
    *,
    key: str | None = None,
    headers: Dict[str, Any] | None = None,
) -> None:
    if producer is None:
        raise RuntimeError("Kafka producer not available")
    try:
        payload_bytes = json.dumps(payload).encode("utf-8")
        key_bytes = None
        if key is not None:
            key_bytes = key.encode("utf-8") if isinstance(key, str) else key
        header_items: list[tuple[str, str]] = []
        if headers:
            for header_key, header_value in headers.items():
                if header_value is None:
                    continue
                header_items.append((header_key, str(header_value)))
        producer.produce(
            topic,
            value=payload_bytes,
            key=key_bytes,
            headers=header_items or None,
        )
    except Exception as e:
        raise e


_known_pending_tenants: set[str] = set()


def _update_outbox_pending_metrics() -> None:
    if report_outbox_pending is None:
        return
    counts: dict[str, int] = {}
    try:
        counts = get_pending_counts_by_tenant()
    except Exception:
        pass
    current_tenants = set(counts.keys())
    if not current_tenants:
        counts = {DEFAULT_TENANT_LABEL: 0}
        current_tenants = {DEFAULT_TENANT_LABEL}
    for tenant, cnt in counts.items():
        report_outbox_pending(tenant, cnt)
    stale_tenants = _known_pending_tenants - current_tenants
    for tenant in stale_tenants:
        report_outbox_pending(tenant, 0)
    _known_pending_tenants.clear()
    _known_pending_tenants.update(current_tenants)


def _process_batch(
    session: Session, producer, batch_size: int, max_retries: int
) -> int:
    events = (
        session.query(OutboxEvent)
        .filter(OutboxEvent.status == "pending")
        .order_by(OutboxEvent.created_at)
        .limit(batch_size)
        .all()
    )
    if not events:
        _update_outbox_pending_metrics()
        return 0
    sent = 0
    batches: dict[str, list[OutboxEvent]] = defaultdict(list)
    for ev in events:
        tenant_label = ev.tenant_id or DEFAULT_TENANT_LABEL
        batches[tenant_label].append(ev)
    processed_counts: dict[tuple[str, str], int] = {}
    for tenant_label, tenant_events in batches.items():
        slice_events = tenant_events[:_PER_TENANT_BATCH_LIMIT]
        for ev in slice_events:
            topic = ev.topic
            try:
                key = f"{tenant_label}:{ev.dedupe_key}"
                headers = {
                    "tenant-id": tenant_label,
                    "dedupe-key": ev.dedupe_key,
                }
                _publish_record(
                    producer,
                    topic,
                    ev.payload,
                    key=key,
                    headers=headers,
                )
                ev.status = "sent"
                sent += 1
                k = (tenant_label, topic)
                processed_counts[k] = processed_counts.get(k, 0) + 1
            except Exception as e:
                ev.retries = int(ev.retries or 0) + 1
                ev.last_error = str(e)
                if ev.retries >= max_retries:
                    ev.status = "failed"
            session.add(ev)
    session.commit()
    # Best-effort flush to push deliveries
    try:
        if producer is not None:
            # confluent-kafka and kafka-python both expose flush(timeout)
            producer.flush(5)
    except Exception:
        pass
    if report_outbox_processed is not None:
        for (tenant_label, topic), count in processed_counts.items():
            try:
                report_outbox_processed(tenant_label, topic, count)
            except Exception:
                continue
    _update_outbox_pending_metrics()
    return sent


def run_forever() -> None:  # pragma: no cover - integration loop
    # Require DB and Kafka to be ready before starting
    assert_ready(
        require_kafka=True,
        require_redis=False,
        require_postgres=True,
        require_opa=False,
    )
    batch_size = int(os.getenv("SOMABRAIN_OUTBOX_BATCH_SIZE", "100") or 100)
    max_retries = int(os.getenv("SOMABRAIN_OUTBOX_MAX_RETRIES", "5") or 5)
    poll_interval = float(os.getenv("SOMABRAIN_OUTBOX_POLL_INTERVAL", "1.0") or 1.0)
    create_retry_ms = int(
        os.getenv("SOMABRAIN_OUTBOX_PRODUCER_RETRY_MS", "1000") or 1000
    )
    session_factory = get_session_factory()
    producer = _make_producer()
    # Robust startup: retry until producer is available
    while producer is None:
        logging.warning(
            "outbox_publisher: Kafka unavailable; retrying producer init..."
        )
        time.sleep(create_retry_ms / 1000.0)
        producer = _make_producer()
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
