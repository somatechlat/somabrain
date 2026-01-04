"""
Transactional Outbox Publisher - Django ORM version

Polls the outbox_events table and publishes events to Kafka topics.
On successful publish, marks the event as 'sent'. On failure, increments retries
and stores last_error; after max retries, marks as 'failed'.

Robustness improvements:
- Prefer confluent-kafka with idempotence + acks=all when available
- Fall back to kafka-python with acks=all and client retries
- Startup waits and retries producer creation until Kafka is reachable
- Per-send errors update retry counters without crashing the loop

Migrated from SQLAlchemy to Django ORM.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional
import logging

# Django setup MUST be called before importing any Django models
# This is required for standalone workers outside of manage.py
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "somabrain.settings")
django.setup()

from django.db import transaction

from somabrain.db.outbox import (
    get_pending_counts_by_tenant,
    get_pending_events_by_tenant_batch,
)
from somabrain.metrics import (
    DEFAULT_TENANT_LABEL,
    report_outbox_pending,
    report_outbox_processed,
)
from somabrain.journal import get_journal
from somabrain.db.outbox_journal import replay_journal_events
from somabrain.common.infra import assert_ready
from somabrain.workers.quota_manager import get_quota_manager
from django.conf import settings

# Per-tenant batch processing configuration
_PER_TENANT_BATCH_LIMIT = max(
    1,
    int(getattr(settings, "OUTBOX_TENANT_BATCH_LIMIT", 50) or 50),
)

# Backpressure configuration
_BACKPRESSURE_ENABLED = (
    str(getattr(settings, "OUTBOX_BACKPRESSURE_ENABLED", "true")).lower() == "true"
)


def _bootstrap() -> Optional[str]:
    # Prefer explicit SOMA_KAFKA_BOOTSTRAP if present (plain host:port)
    """Execute bootstrap."""

    direct = (getattr(settings, "KAFKA_BOOTSTRAP", "") or "").strip()
    if direct:
        return direct
    url = getattr(settings, "KAFKA_BOOTSTRAP_SERVERS", "")
    if not url:
        return None
    return url.replace("kafka://", "").strip()


def _make_producer():  # pragma: no cover - optional at runtime
    """Execute make producer."""

    bootstrap = _bootstrap()
    if not bootstrap:
        return None
    try:
        from confluent_kafka import Producer

        # Enhanced producer configuration for idempotency and reliability
        conf = {
            "bootstrap.servers": bootstrap,
            "enable.idempotence": True,
            "acks": "all",
            "retries": 2147483647,  # Retry indefinitely within timeout
            "max.in.flight.requests.per.connection": 5,  # Maintain throughput with idempotence
            "compression.type": "snappy",
            "linger.ms": 5,  # Small batching for efficiency
            "batch.size": 16384,  # 16KB batch size
            "delivery.timeout.ms": 30000,  # 30 second timeout
            "request.timeout.ms": 30000,  # 30 second request timeout
            "socket.timeout.ms": 30000,  # 30 second socket timeout
            "client.id": f"somabrain-outbox-{os.getpid()}",
        }
        return Producer(conf)
    except Exception as exc:
        logging.warning("Failed to create Kafka producer: %s", exc)
        return None


def _publish_record(
    producer,
    topic: str,
    payload: Dict[str, Any],
    *,
    key: str | None = None,
    headers: Dict[str, Any] | None = None,
) -> None:
    """Publish a record to Kafka with enhanced keying and headers for idempotency."""
    if producer is None:
        raise RuntimeError("Kafka producer not available")
    try:
        # Serialize payload
        payload_bytes = json.dumps(
            payload, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")

        # Handle key encoding with validation
        key_bytes = None
        if key is not None:
            if isinstance(key, str):
                key_bytes = key.encode("utf-8")
            elif isinstance(key, bytes):
                key_bytes = key
            else:
                key_bytes = str(key).encode("utf-8")

        # Build headers with standard outbox headers
        header_items: list[tuple[str, bytes]] = []

        # Add timestamp header
        timestamp_ms = int(time.time() * 1000)
        header_items.append(("x-timestamp-ms", str(timestamp_ms).encode("utf-8")))

        # Add version header for schema evolution
        header_items.append(("x-schema-version", "1.0".encode("utf-8")))

        # Add producer identification
        header_items.append(
            ("x-producer-id", f"somabrain-outbox-{os.getpid()}".encode("utf-8"))
        )

        # Add custom headers
        if headers:
            for header_key, header_value in headers.items():
                if header_value is None:
                    continue
                header_key_str = str(header_key).lower().replace("_", "-")
                header_value_str = str(header_value)
                header_items.append((header_key_str, header_value_str.encode("utf-8")))

        # Publish with all metadata
        producer.produce(
            topic,
            value=payload_bytes,
            key=key_bytes,
            headers=header_items or None,
        )

    except Exception as e:
        # Enhance error with context
        error_msg = f"Failed to publish to topic '{topic}'"
        if key:
            error_msg += f" with key '{key}'"
        error_msg += f": {e}"
        raise RuntimeError(error_msg) from e


_known_pending_tenants: set[str] = set()


def _update_outbox_pending_metrics() -> None:
    """Execute update outbox pending metrics."""

    if report_outbox_pending is None:
        return
    counts: dict[str, int] = {}
    try:
        counts = get_pending_counts_by_tenant()
    except Exception as exc:
        logging.debug("Failed to get pending counts by tenant: %s", exc)
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


@transaction.atomic
def _process_batch(producer, batch_size: int, max_retries: int) -> int:
    """Process a batch of outbox events using Django ORM."""
    # Get quota manager for tenant rate limiting
    quota_manager = get_quota_manager()

    # Use tenant-aware batch processing to prevent any single tenant from dominating
    tenant_batches = get_pending_events_by_tenant_batch(
        limit_per_tenant=_PER_TENANT_BATCH_LIMIT,
        max_tenants=max(1, batch_size // _PER_TENANT_BATCH_LIMIT),
    )

    if not tenant_batches:
        _update_outbox_pending_metrics()
        return 0

    sent = 0
    processed_counts: dict[tuple[str, str], int] = {}
    skipped_tenants = set()

    # Process events tenant by tenant with quota enforcement
    for tenant_label, tenant_events in tenant_batches.items():
        # Check quota before processing tenant events
        if _BACKPRESSURE_ENABLED and not quota_manager.can_process(
            tenant_label, len(tenant_events)
        ):
            skipped_tenants.add(tenant_label)
            continue

        tenant_processed = 0
        for ev in tenant_events:
            topic = ev.topic
            try:
                # Generate stable key for idempotency: tenant:dedupe_key
                key = (
                    f"{tenant_label}:{ev.dedupe_key}"
                    if ev.dedupe_key
                    else f"{tenant_label}:{ev.id}"
                )

                # Build comprehensive headers for tracing and context
                headers = {
                    "tenant-id": tenant_label,
                    "dedupe-key": ev.dedupe_key or "",
                    "event-id": str(ev.id),
                    "event-topic": ev.topic,
                    "event-created-at": (
                        ev.created_at.isoformat() if ev.created_at else ""
                    ),
                    "retry-count": str(ev.retries or 0),
                    "processing-attempt": str(ev.retries + 1),
                }

                _publish_record(
                    producer,
                    topic,
                    ev.payload,
                    key=key,
                    headers=headers,
                )
                ev.status = "sent"
                ev.save()
                sent += 1
                tenant_processed += 1
                k = (tenant_label, topic)
                processed_counts[k] = processed_counts.get(k, 0) + 1

                # Update journal event status
                journal = get_journal()
                journal.mark_events_sent([ev.dedupe_key])
            except Exception as e:
                ev.retries = int(ev.retries or 0) + 1
                ev.last_error = str(e)
                if ev.retries >= max_retries:
                    ev.status = "failed"
                ev.save()

        # Record usage for successfully processed tenant
        if tenant_processed > 0:
            quota_manager.record_usage(tenant_label, tenant_processed)

    # Best-effort flush to push deliveries
    try:
        if producer is not None:
            producer.flush(5)
    except Exception as exc:
        logging.debug("Failed to flush Kafka producer: %s", exc)

    # Report processed events
    if report_outbox_processed is not None:
        for (tenant_label, topic), count in processed_counts.items():
            try:
                report_outbox_processed(tenant_label, topic, count)
            except Exception as exc:
                logging.debug(
                    "Failed to report outbox processed for tenant=%s topic=%s: %s",
                    tenant_label,
                    topic,
                    exc,
                )
                continue

    # Log skipped tenants due to quota limits
    if skipped_tenants:
        logging.info(
            "outbox_publisher: Skipped processing for %d tenants due to quota limits: %s",
            len(skipped_tenants),
            ", ".join(sorted(skipped_tenants)),
        )

    # Periodic cleanup of old tenant data
    if sent == 0:  # Only cleanup on idle cycles
        quota_manager.cleanup_old_tenants()

    _update_outbox_pending_metrics()
    return sent


def run_forever() -> None:  # pragma: no cover - integration loop
    # Require DB and Kafka to be ready before starting
    """Execute run forever."""

    assert_ready(
        require_kafka=True,
        require_redis=False,
        require_postgres=True,
        require_opa=False,
    )
    batch_size = int(settings.OUTBOX_BATCH_SIZE or 100)
    max_retries = int(getattr(settings, "OUTBOX_MAX_RETRIES", 5) or 5)
    poll_interval = float(getattr(settings, "OUTBOX_POLL_INTERVAL", 1.0) or 1.0)
    create_retry_ms = int(getattr(settings, "OUTBOX_PRODUCER_RETRY_MS", 1000) or 1000)
    journal_replay_interval = int(
        getattr(settings, "JOURNAL_REPLAY_INTERVAL", 300) or 300
    )  # 5 minutes

    producer = _make_producer()

    # Robust startup: retry until producer is available
    while producer is None:
        logging.warning(
            "outbox_publisher: Kafka unavailable; retrying producer init..."
        )
        time.sleep(create_retry_ms / 1000.0)
        producer = _make_producer()

    last_journal_replay = time.time()

    while True:
        current_time = time.time()

        # Periodically replay journal events to database
        if current_time - last_journal_replay >= journal_replay_interval:
            replayed = replay_journal_events(limit=batch_size)
            if replayed > 0:
                logging.info(f"Replayed {replayed} events from journal to database")
            last_journal_replay = current_time

        # Process regular database outbox events
        try:
            n = _process_batch(producer, batch_size, max_retries)
        except Exception as e:
            # Safety net: don't crash the loop on DB issues
            logging.error("outbox_publisher: batch error: %s", e)
            n = 0

        # Only sleep if no events were processed
        if n == 0:
            time.sleep(poll_interval)


def main() -> None:  # pragma: no cover
    """Execute main."""

    run_forever()


if __name__ == "__main__":  # pragma: no cover
    main()
