"""
Transactional Outbox Publisher - Django ORM version

Polls the outbox_events table and drains events to their terminal destination.

T-6: for ``memory.store`` events the terminal condition is a STORE ack
(``memsvc.aremember``) — not a Kafka publish. Only after the store accepts
the write is the row marked ``sent``. Kafka publication, when it succeeds, is
secondary and best-effort. The same terminal condition is enforced in-process
by ``api/endpoints/memory_remember._replay_pending_to_store``.

On failure, increments retries and stores last_error; after max retries,
marks as 'failed'.

Robustness improvements:
- Prefer confluent-kafka with idempotence + acks=all when available
- Fall back to kafka-python with acks=all and client retries
- Startup waits and retries producer creation until Kafka is reachable
- Per-send errors update retry counters without crashing the loop

Migrated from SQLAlchemy to Django ORM.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

# Django setup MUST be called before importing any Django models
# This is required for standalone workers outside of manage.py
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "somabrain.settings")
django.setup()

from django.conf import settings

from common.infra_utils import assert_ready
from somabrain.db.outbox import (
    claim_pending_events,
    get_pending_counts_by_tenant,
    mark_events_failed_bulk,
    mark_events_sent_bulk,
)
from somabrain.settings.resolve import UnconfiguredServiceError, require_tenant
from somabrain.db.outbox_journal import replay_journal_events
from somabrain.journal import get_journal
from somabrain.metrics import (
    DEFAULT_TENANT_LABEL,
    report_outbox_pending,
    report_outbox_processed,
)
from somabrain.workers.quota_manager import get_quota_manager

# Per-tenant batch processing configuration
_PER_TENANT_BATCH_LIMIT = max(
    1,
    int(getattr(settings, "OUTBOX_TENANT_BATCH_LIMIT") or 50),
)

# Backpressure configuration
_BACKPRESSURE_ENABLED = (
    str(getattr(settings, "OUTBOX_BACKPRESSURE_ENABLED")).lower() == "true"
)


def _bootstrap() -> str | None:
    # Prefer explicit KAFKA_BOOTSTRAP if present (plain host:port).
    # confluent-kafka rejects schemes like ``kafka://`` — always strip.
    """Execute bootstrap."""

    raw = (getattr(settings, "KAFKA_BOOTSTRAP") or "").strip()
    if not raw:
        raw = (getattr(settings, "KAFKA_BOOTSTRAP_SERVERS") or "").strip()
    if not raw:
        return None
    text = raw
    for scheme in ("kafka://", "kafka+ssl://", "ssl://", "plaintext://"):
        if text.startswith(scheme):
            text = text[len(scheme) :]
    return text.strip().strip("/")


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
    payload: dict[str, Any],
    *,
    key: str | None = None,
    headers: dict[str, Any] | None = None,
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
        header_items.append(("x-schema-version", b"1.0"))

        # Add producer identification
        header_items.append(
            ("x-producer-id", f"somabrain-outbox-{os.getpid()}".encode())
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


def _event_store_key(ev) -> str:
    """Store key for a ``memory.store`` row (coord identity, never a UUID)."""
    payload = dict(ev.payload or {})
    key = payload.get("key")
    if key is not None:
        return str(key)
    coord = payload.get("coord")
    if coord is not None:
        if isinstance(coord, str):
            return coord.strip()
        return f"{coord[0]},{coord[1]},{coord[2]}"
    raise ValueError(
        f"memory.store outbox event id={ev.id} has neither key nor coord "
        "in its payload; cannot write to the store"
    )


def _write_memory_to_store(tenant_label: str, ev) -> bool:
    """Write one ``memory.store`` event to the STORE via ``memsvc.aremember``.

    T-6: only a store ack closes an event. A Kafka publish is NOT a store
    ack. Returns True when the store accepted the write. Raises on any
    failure so the caller leaves the row pending for replay — the same
    terminal condition as ``api/endpoints/memory_remember._replay_pending_to_store``.
    """
    from django.db import close_old_connections

    from asgiref.sync import async_to_sync

    from somabrain.api.memory.helpers import _get_memory_pool, _resolve_namespace
    from somabrain.services.memory_service import MemoryService

    # Thread-pool workers must not inherit a parent connection or leak them.
    close_old_connections()
    try:
        key = _event_store_key(ev)
        payload = dict(ev.payload or {})
        stored = payload.get("payload") or payload
        ns = stored.get("namespace") or ""
        pool = _get_memory_pool()
        if pool is None:
            raise RuntimeError("memory pool unavailable")
        memsvc = MemoryService(pool, _resolve_namespace(tenant_label, ns))
        async_to_sync(memsvc.aremember)(key, stored)
        return True
    finally:
        close_old_connections()


def _write_memory_batch_to_store(tenant_label: str, events: list) -> dict[int, Exception | None]:
    """Drain a tenant's ``memory.store`` batch concurrently to SFM.

    Returns ``{event_id: None | exception}``. T-6 is unchanged: a row is only
    marked sent when its own store ack succeeded. Failures stay claimable for
    replay. Concurrency uses a bounded thread pool over the shared HTTP
    transport (httpx connection pool) so one slow SFM RTT cannot serialize the
    whole drain — the million-txn / ms-latency requirement.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    results: dict[int, Exception | None] = {}
    if not events:
        return results

    # Single-item path is the common small-batch case.
    if len(events) == 1:
        ev = events[0]
        try:
            _write_memory_to_store(tenant_label, ev)
            results[int(ev.id)] = None
        except Exception as exc:  # noqa: BLE001 — per-row isolation
            results[int(ev.id)] = exc
        return results

    from somabrain.settings.resolve import require_setting

    workers = min(len(events), int(require_setting("OUTBOX_SFM_WRITE_WORKERS")))
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="outbox-sfm") as pool:
        futures = {
            pool.submit(_write_memory_to_store, tenant_label, ev): ev for ev in events
        }
        for fut in as_completed(futures):
            ev = futures[fut]
            try:
                fut.result()
                results[int(ev.id)] = None
            except Exception as exc:  # noqa: BLE001
                results[int(ev.id)] = exc
    return results


def _process_batch(producer, batch_size: int, max_retries: int) -> int:
    """Drain a claimed slice of the outbox to SFM (and Kafka secondary).

    Million-txn / ms-latency design:
    1. ``claim_pending_events`` — short ``FOR UPDATE SKIP LOCKED`` transaction
       so publisher replicas take disjoint slices.
    2. **No** DB transaction spans SFM/network I/O (the previous
       ``@transaction.atomic`` held row locks across every RTT).
    3. Per-tenant concurrent ``memory.store`` writes via the HTTP pool.
    4. Bulk ``mark_events_sent_bulk`` / failure accounting after acks.

    T-6 unchanged: a row is ``sent`` only after its store ack.
    """
    quota_manager = get_quota_manager()

    claimed = claim_pending_events(batch_size)
    if not claimed:
        _update_outbox_pending_metrics()
        return 0

    by_tenant: dict[str, list] = {}
    for ev in claimed:
        tenant_id = ev.tenant_id
        if tenant_id is None or not str(tenant_id).strip():
            raise UnconfiguredServiceError(
                f"outbox event id={ev.id} has a missing tenant_id; refusing to "
                "publish into a default tenant (T-5)."
            )
        label = require_tenant(tenant_id)
        by_tenant.setdefault(label, []).append(ev)

    sent_ids: list[int] = []
    failures: list[tuple[int, str]] = []
    processed_counts: dict[tuple[str, str], int] = {}
    skipped_tenants: set[str] = set()
    journal_keys: list[str] = []

    for tenant_label, tenant_events in by_tenant.items():
        if _BACKPRESSURE_ENABLED and not quota_manager.can_process(
            tenant_label, len(tenant_events)
        ):
            skipped_tenants.add(tenant_label)
            # Leave rows claimed-as-pending: next cycle re-reads them.
            continue

        store_events = [ev for ev in tenant_events if ev.topic == "memory.store"]
        other_events = [ev for ev in tenant_events if ev.topic != "memory.store"]

        # --- memory.store: concurrent SFM, T-6 per row ---
        store_results = _write_memory_batch_to_store(tenant_label, store_events)
        for ev in store_events:
            err = store_results.get(int(ev.id), RuntimeError("missing store result"))
            if err is None:
                sent_ids.append(int(ev.id))
                journal_keys.append(ev.dedupe_key or str(ev.id))
                k = (str(tenant_label), str(ev.topic))
                processed_counts[k] = processed_counts.get(k, 0) + 1
                try:
                    key = (
                        f"{tenant_label}:{ev.dedupe_key}"
                        if ev.dedupe_key
                        else f"{tenant_label}:{ev.id}"
                    )
                    _publish_record(
                        producer,
                        ev.topic,
                        ev.payload,
                        key=key,
                        headers={
                            "tenant-id": tenant_label,
                            "dedupe-key": ev.dedupe_key or "",
                            "event-id": str(ev.id),
                            "event-topic": ev.topic,
                        },
                    )
                except Exception as kafka_exc:
                    logging.debug(
                        "outbox_publisher: secondary Kafka publish failed "
                        "for event id=%s (store already acked): %s",
                        ev.id,
                        kafka_exc,
                    )
            else:
                failures.append((int(ev.id), str(err)))

        # --- other topics: Kafka is terminal ---
        for ev in other_events:
            try:
                key = (
                    f"{tenant_label}:{ev.dedupe_key}"
                    if ev.dedupe_key
                    else f"{tenant_label}:{ev.id}"
                )
                _publish_record(
                    producer,
                    ev.topic,
                    ev.payload,
                    key=key,
                    headers={
                        "tenant-id": tenant_label,
                        "dedupe-key": ev.dedupe_key or "",
                        "event-id": str(ev.id),
                        "event-topic": ev.topic,
                    },
                )
                sent_ids.append(int(ev.id))
                journal_keys.append(ev.dedupe_key or str(ev.id))
                k = (str(tenant_label), str(ev.topic))
                processed_counts[k] = processed_counts.get(k, 0) + 1
            except Exception as exc:  # noqa: BLE001
                failures.append((int(ev.id), str(exc)))

        tenant_sent = sum(
            1
            for ev in tenant_events
            if int(ev.id) in set(sent_ids)
        )
        if tenant_sent:
            quota_manager.record_usage(tenant_label, tenant_sent)

    if sent_ids:
        mark_events_sent_bulk(sent_ids)
    if failures:
        mark_events_failed_bulk(failures, max_retries=max_retries)

    if journal_keys:
        try:
            get_journal().mark_events_sent(journal_keys)
        except Exception as exc:
            logging.debug("outbox_publisher: journal mark sent failed: %s", exc)

    try:
        if producer is not None:
            producer.flush(5)
    except Exception as exc:
        logging.debug("Failed to flush Kafka producer: %s", exc)

    if report_outbox_processed is not None:
        for tenant_label, topic in processed_counts:
            count = processed_counts.get((str(tenant_label), str(topic)), 0)
            try:
                report_outbox_processed(str(tenant_label), str(topic), count)
            except Exception as exc:
                logging.debug(
                    "Failed to report outbox processed for tenant=%s topic=%s: %s",
                    str(tenant_label),
                    str(topic),
                    exc,
                )

    if skipped_tenants:
        logging.info(
            "outbox_publisher: Skipped processing for %d tenants due to quota limits: %s",
            len(skipped_tenants),
            ", ".join(sorted(skipped_tenants)),
        )

    if not sent_ids:
        quota_manager.cleanup_old_tenants()

    _update_outbox_pending_metrics()
    return len(sent_ids)


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
    max_retries = int(getattr(settings, "OUTBOX_MAX_RETRIES") or 5)
    poll_interval = float(getattr(settings, "OUTBOX_POLL_INTERVAL") or 1.0)
    create_retry_ms = int(getattr(settings, "OUTBOX_PRODUCER_RETRY_MS") or 1000)
    journal_replay_interval = int(
        getattr(settings, "JOURNAL_REPLAY_INTERVAL") or 300
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
            replayed = replay_journal_events(limit=batch_size)  # type: ignore
            if replayed > 0:
                logging.info(f"Replayed {replayed} events from journal to database")
            last_journal_replay = current_time

        # Process regular database outbox events
        try:
            n = _process_batch(producer, batch_size, max_retries)
        except Exception as e:  # type: ignore
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
