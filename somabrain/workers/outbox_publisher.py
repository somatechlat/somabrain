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
import threading
from collections import defaultdict
from typing import Any, Dict, Optional
import logging

from sqlalchemy.orm import Session

from somabrain.db.models.outbox import OutboxEvent
from somabrain.db.outbox import get_pending_counts_by_tenant, get_pending_events_by_tenant_batch
from somabrain.metrics import (
    DEFAULT_TENANT_LABEL,
    report_outbox_pending,
    report_outbox_processed,
)
from somabrain.journal import get_journal
from somabrain.db.outbox import replay_journal_events
from somabrain.storage.db import get_session_factory
from somabrain.common.infra import assert_ready

# Per-tenant batch processing configuration
_PER_TENANT_BATCH_LIMIT = max(
    1,
    int(settings.getenv("SOMABRAIN_OUTBOX_TENANT_BATCH_LIMIT", "50") or 50),
)

# Per-tenant quota configuration
_PER_TENANT_QUOTA_LIMIT = max(
    1,
    int(settings.getenv("SOMABRAIN_OUTBOX_TENANT_QUOTA_LIMIT", "1000") or 1000),
)

# Per-tenant quota window in seconds
_PER_TENANT_QUOTA_WINDOW = max(
    1,
    int(settings.getenv("SOMABRAIN_OUTBOX_TENANT_QUOTA_WINDOW", "60") or 60),
)

# Backpressure configuration
_BACKPRESSURE_ENABLED = settings.getenv("SOMABRAIN_OUTBOX_BACKPRESSURE_ENABLED", "true").lower() == "true"
_BACKPRESSURE_THRESHOLD = max(
    0.1,
    float(settings.getenv("SOMABRAIN_OUTBOX_BACKPRESSURE_THRESHOLD", "0.8") or 0.8),
)


def _bootstrap() -> Optional[str]:
    # Prefer explicit SOMA_KAFKA_BOOTSTRAP if present (plain host:port)
    direct = (settings.getenv("SOMA_KAFKA_BOOTSTRAP") or "").strip()
    if direct:
        return direct
    url = settings.getenv("SOMABRAIN_KAFKA_URL")
    if not url:
        return None
    return url.replace("kafka://", "").strip()


def _make_producer():  # pragma: no cover - optional at runtime
    bootstrap = _bootstrap()
    if not bootstrap:
        return None
    try:
        from confluent_kafka import Producer  # type: ignore

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
    """Publish a record to Kafka with enhanced keying and headers for idempotency.
    
    Args:
        producer: Kafka producer instance
        topic: Target topic
        payload: Event payload to publish
        key: Stable key for idempotency (typically tenant:dedupe_key)
        headers: Additional headers for context and tracing
    
    Raises:
        RuntimeError: If producer is not available
        Exception: If publishing fails
    """
    if producer is None:
        raise RuntimeError("Kafka producer not available")
    try:
        # Serialize payload
        payload_bytes = json.dumps(payload, separators=(',', ':'), ensure_ascii=False).encode("utf-8")
        
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
        import time
        timestamp_ms = int(time.time() * 1000)
        header_items.append(("x-timestamp-ms", str(timestamp_ms).encode("utf-8")))
        
        # Add version header for schema evolution
        header_items.append(("x-schema-version", "1.0".encode("utf-8")))
        
        # Add producer identification
        header_items.append(("x-producer-id", f"somabrain-outbox-{os.getpid()}".encode("utf-8")))
        
        # Add custom headers
        if headers:
            for header_key, header_value in headers.items():
                if header_value is None:
                    continue
                header_key_str = str(header_key).lower().replace('_', '-')
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


class TenantQuotaManager:
    """Manages per-tenant processing quotas and backpressure."""
    
    def __init__(self, quota_limit: int, quota_window: int):
        self.quota_limit = quota_limit
        self.quota_window = quota_window
        self.tenant_usage: dict[str, list[float]] = {}  # tenant -> list of timestamps
        self.tenant_backoff: dict[str, float] = {}  # tenant -> backoff until timestamp
        self._lock = threading.RLock()
    
    def can_process(self, tenant_id: str, count: int = 1) -> bool:
        """Check if tenant can process requested number of events.
        
        Args:
            tenant_id: The tenant identifier
            count: Number of events to process
            
        Returns:
            True if within quota, False if would exceed quota
        """
        with self._lock:
            now = time.time()
            tenant = tenant_id or "default"
            
            # Check if tenant is in backoff
            backoff_until = self.tenant_backoff.get(tenant, 0.0)
            if now < backoff_until:
                return False
            
            # Clean old usage records
            usage_times = self.tenant_usage.get(tenant, [])
            cutoff_time = now - self.quota_window
            recent_usage = [t for t in usage_times if t > cutoff_time]
            
            # Check quota
            if len(recent_usage) + count > self.quota_limit:
                # Apply backoff
                backoff_duration = min(self.quota_window, max(5.0, self.quota_window * 0.1))
                self.tenant_backoff[tenant] = now + backoff_duration
                return False
            
            return True
    
    def record_usage(self, tenant_id: str, count: int = 1) -> None:
        """Record processing usage for a tenant.
        
        Args:
            tenant_id: The tenant identifier
            count: Number of events processed
        """
        with self._lock:
            now = time.time()
            tenant = tenant_id or "default"
            
            # Record usage
            if tenant not in self.tenant_usage:
                self.tenant_usage[tenant] = []
            
            for _ in range(count):
                self.tenant_usage[tenant].append(now)
            
            # Clear backoff on successful processing
            if tenant in self.tenant_backoff:
                del self.tenant_backoff[tenant]
    
    def get_usage_stats(self) -> dict[str, dict[str, Any]]:
        """Get current usage statistics for all tenants.
        
        Returns:
            Dict mapping tenant IDs to their usage statistics
        """
        with self._lock:
            now = time.time()
            stats = {}
            cutoff_time = now - self.quota_window
            
            for tenant, usage_times in self.tenant_usage.items():
                recent_usage = [t for t in usage_times if t > cutoff_time]
                backoff_until = self.tenant_backoff.get(tenant, 0.0)
                
                stats[tenant] = {
                    "current_usage": len(recent_usage),
                    "quota_limit": self.quota_limit,
                    "usage_ratio": len(recent_usage) / self.quota_limit,
                    "in_backoff": now < backoff_until,
                    "backoff_remaining": max(0.0, backoff_until - now),
                }
            
            return stats
    
    def cleanup_old_tenants(self, max_age: float = 300.0) -> None:
        """Clean up old tenant data to prevent memory leaks.
        
        Args:
            max_age: Maximum age in seconds for tenant data
        """
        with self._lock:
            now = time.time()
            cutoff_time = now - max_age
            
            # Clean old usage records
            for tenant in list(self.tenant_usage.keys()):
                usage_times = self.tenant_usage[tenant]
                recent_usage = [t for t in usage_times if t > cutoff_time]
                
                if not recent_usage:
                    del self.tenant_usage[tenant]
                    if tenant in self.tenant_backoff:
                        del self.tenant_backoff[tenant]
                else:
                    self.tenant_usage[tenant] = recent_usage


# Global quota manager instance
_quota_manager: Optional[TenantQuotaManager] = None


def get_quota_manager() -> TenantQuotaManager:
    """Get or create the global quota manager instance."""
    global _quota_manager
    if _quota_manager is None:
        _quota_manager = TenantQuotaManager(_PER_TENANT_QUOTA_LIMIT, _PER_TENANT_QUOTA_WINDOW)
    return _quota_manager


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
    # Get quota manager for tenant rate limiting
    quota_manager = get_quota_manager()
    
    # Use tenant-aware batch processing to prevent any single tenant from dominating
    tenant_batches = get_pending_events_by_tenant_batch(
        limit_per_tenant=_PER_TENANT_BATCH_LIMIT,
        max_tenants=max(1, batch_size // _PER_TENANT_BATCH_LIMIT)
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
        if _BACKPRESSURE_ENABLED and not quota_manager.can_process(tenant_label, len(tenant_events)):
            skipped_tenants.add(tenant_label)
            continue
            
        tenant_processed = 0
        for ev in tenant_events:
            topic = ev.topic
            try:
                # Generate stable key for idempotency: tenant:dedupe_key
                # This ensures same event always gets same key for exactly-once semantics
                key = f"{tenant_label}:{ev.dedupe_key}" if ev.dedupe_key else f"{tenant_label}:{ev.id}"
                
                # Build comprehensive headers for tracing and context
                headers = {
                    "tenant-id": tenant_label,
                    "dedupe-key": ev.dedupe_key or "",
                    "event-id": str(ev.id),
                    "event-topic": ev.topic,
                    "event-created-at": ev.created_at.isoformat() if ev.created_at else "",
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
            session.add(ev)
        
        # Record usage for successfully processed tenant
        if tenant_processed > 0:
            quota_manager.record_usage(tenant_label, tenant_processed)
    
    session.commit()
    
    # Best-effort flush to push deliveries
    try:
        if producer is not None:
            # confluent-kafka and kafka-python both expose flush(timeout)
            producer.flush(5)
    except Exception:
        pass
        
    # Report processed events
    if report_outbox_processed is not None:
        for (tenant_label, topic), count in processed_counts.items():
            try:
                report_outbox_processed(tenant_label, topic, count)
            except Exception:
                continue
    
    # Log skipped tenants due to quota limits
    if skipped_tenants:
        logging.info(
            "outbox_publisher: Skipped processing for %d tenants due to quota limits: %s",
            len(skipped_tenants),
            ", ".join(sorted(skipped_tenants))
        )
    
    # Periodic cleanup of old tenant data
    if sent == 0:  # Only cleanup on idle cycles
        quota_manager.cleanup_old_tenants()
    
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
    batch_size = int(settings.getenv("SOMABRAIN_OUTBOX_BATCH_SIZE", "100") or 100)
    max_retries = int(settings.getenv("SOMABRAIN_OUTBOX_MAX_RETRIES", "5") or 5)
    poll_interval = float(settings.getenv("SOMABRAIN_OUTBOX_POLL_INTERVAL", "1.0") or 1.0)
    create_retry_ms = int(
        settings.getenv("SOMABRAIN_OUTBOX_PRODUCER_RETRY_MS", "1000") or 1000
    )
    journal_replay_interval = int(settings.getenv("SOMABRAIN_JOURNAL_REPLAY_INTERVAL", "300") or 300)  # 5 minutes
    
    session_factory = get_session_factory()
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
        with session_factory() as session:
            try:
                n = _process_batch(session, producer, batch_size, max_retries)
            except Exception as e:
                # Safety net: don't crash the loop on DB issues
                logging.error("outbox_publisher: batch error: %s", e)
                n = 0
        
        # Only sleep if no events were processed from either source
        if n == 0:
            time.sleep(poll_interval)


def main() -> None:  # pragma: no cover
    run_forever()


if __name__ == "__main__":  # pragma: no cover
    main()
