"""
Transactional outbox DB operations using Django ORM.

Per Requirements E2.1-E2.5:
- E2.1: remember() records to outbox before SFM call  
- E2.2: Mark "sent" on success
- E2.3: Remain "pending" on failure for retry
- E2.4: Duplicate detection via idempotency key  
- E2.5: Backpressure when outbox > 10000 entries

Migrated from SQLAlchemy to Django ORM.
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from somabrain.models import OutboxEvent
from somabrain.journal import get_journal, JournalEvent

logger = logging.getLogger(__name__)

VALID_OUTBOX_STATUSES = {"pending", "sent", "failed"}

# Memory operation topics per Task 10.1
MEMORY_TOPICS: Dict[str, str] = {
    "memory.store": "Store memory to SFM",
    "memory.bulk_store": "Bulk store memories to SFM",
    "memory.delete": "Delete memory from SFM",
    "graph.link": "Create graph link in SFM",
    "graph.delete_link": "Delete graph link in SFM",
    "wm.persist": "Persist WM item to SFM",
    "wm.evict": "Mark WM item as evicted in SFM",
    "wm.promote": "Promote WM item to LTM",
}

# Backpressure threshold per E2.5
OUTBOX_BACKPRESSURE_THRESHOLD = 10000


class OutboxBackpressureError(Exception):
    """Raised when outbox exceeds backpressure threshold.
    
    Per Requirement E2.5: Backpressure when outbox > 10000 entries.
    """
    
    def __init__(
        self, pending_count: int, threshold: int = OUTBOX_BACKPRESSURE_THRESHOLD
    ):
        """Initialize the instance."""

        self.pending_count = pending_count
        self.threshold = threshold
        super().__init__(
            f"Outbox backpressure: {pending_count} pending events exceeds threshold {threshold}"
        )


def _idempotency_key(
    operation: str,
    coord: Optional[Tuple[float, float, float]] = None,
    tenant: str = "default",
    extra: Optional[str] = None,
) -> str:
    """Generate idempotency key for deduplication.
    
    Per Requirement E2.4: Duplicate detection via idempotency key.
    """
    parts = [operation, tenant]
    if coord is not None:
        parts.append(f"{coord[0]:.6f},{coord[1]:.6f},{coord[2]:.6f}")
    if extra:
        parts.append(extra)
    data = ":".join(parts)
    return hashlib.sha256(data.encode()).hexdigest()[:32]


def check_backpressure(tenant_id: Optional[str] = None) -> bool:
    """Check if outbox is under backpressure.
    
    Per Requirement E2.5: Returns True if pending count exceeds threshold.
    """
    pending = get_pending_count(tenant_id=tenant_id)
    return pending >= OUTBOX_BACKPRESSURE_THRESHOLD


def enqueue_memory_event(
    topic: str,
    payload: Dict[str, Any],
    tenant_id: str,
    coord: Optional[Tuple[float, float, float]] = None,
    extra_key: Optional[str] = None,
    check_backpressure_flag: bool = True,
) -> str:
    """Enqueue a memory operation event with idempotency key.
    
    Per Requirements E2.1-E2.5.
    """
    if topic not in MEMORY_TOPICS:
        logger.warning(f"Unknown memory topic: {topic}, proceeding anyway")
    
    # Check backpressure per E2.5
    if check_backpressure_flag and check_backpressure(tenant_id):
        pending = get_pending_count(tenant_id)
        raise OutboxBackpressureError(pending)
    
    # Generate idempotency key per E2.4
    dedupe_key = _idempotency_key(
        operation=topic,
        coord=coord,
        tenant=tenant_id,
        extra=extra_key,
    )
    
    # Enqueue the event
    enqueue_event(
        topic=topic,
        payload=payload,
        dedupe_key=dedupe_key,
        tenant_id=tenant_id,
    )
    
    logger.debug(
        f"Enqueued memory event: topic={topic}, tenant={tenant_id}, dedupe_key={dedupe_key}"
    )
    
    return dedupe_key


@transaction.atomic
def mark_event_sent(event_id: int) -> bool:
    """Mark an outbox event as sent.
    
    Per Requirement E2.2: Mark "sent" on success.
    """
    updated = OutboxEvent.objects.filter(id=event_id).update(status='sent')
    return updated > 0


@transaction.atomic
def mark_event_failed(event_id: int, error: str) -> bool:
    """Mark an outbox event as failed with error message.
    
    Per Requirement E2.3: Remain "pending" for retry, but track failures.
    """
    from django.db.models import F
    
    updated = OutboxEvent.objects.filter(id=event_id).update(
        status='failed',
        last_error=error[:1000] if error else None,
        retries=F('retries') + 1
    )
    return updated > 0


def get_event_by_dedupe_key(
    dedupe_key: str,
    tenant_id: Optional[str] = None,
) -> Optional[OutboxEvent]:
    """Get an outbox event by its deduplication key.
    
    Per Requirement E2.4: Used for duplicate detection.
    """
    qs = OutboxEvent.objects.filter(dedupe_key=dedupe_key)
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    return qs.first()


def is_duplicate_event(
    dedupe_key: str,
    tenant_id: Optional[str] = None,
) -> bool:
    """Check if an event with this dedupe_key already exists.
    
    Per Requirement E2.4: Duplicate detection.
    """
    return get_event_by_dedupe_key(dedupe_key, tenant_id) is not None


@transaction.atomic
def enqueue_event(
    topic: str,
    payload: Dict[str, Any],
    dedupe_key: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> OutboxEvent:
    """Enqueue a new event to the outbox.
    
    Returns the created OutboxEvent instance.
    """
    if dedupe_key is None:
        dedupe_key = str(uuid.uuid4())
    
    event = OutboxEvent.objects.create(
        topic=topic,
        payload=payload,
        dedupe_key=dedupe_key,
        tenant_id=tenant_id,
        status='pending',
    )
    
    # Write to journal for redundancy and durability
    journal = get_journal()
    journal_event = JournalEvent(
        id=event.id,
        topic=topic,
        payload=payload,
        tenant_id=tenant_id,
        dedupe_key=dedupe_key,
        status="pending",
    )
    journal.append_event(journal_event)
    
    return event


def get_pending_events(
    limit: int = 100, tenant_id: Optional[str] = None
) -> List[OutboxEvent]:
    """Fetch a batch of pending events from the outbox.
    
    Uses the optimized index ix_outbox_status_tenant_created for efficient queries.
    """
    qs = OutboxEvent.objects.filter(status='pending')
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    # Order by created_at to ensure FIFO processing
    return list(qs.order_by('created_at')[:limit])


def list_events_by_status(
    status: str = "pending",
    tenant_id: Optional[str] = None,
    topic_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[OutboxEvent]:
    """List outbox events by status with filtering options.
    
    Provides comprehensive filtering for admin endpoints.
    """
    if status not in VALID_OUTBOX_STATUSES:
        raise ValueError(f"Invalid outbox status: {status}")
    
    limit = max(1, min(int(limit), 500))
    offset = max(0, int(offset))
    
    qs = OutboxEvent.objects.filter(status=status)
    
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    
    if topic_filter:
        qs = qs.filter(topic__icontains=topic_filter)
    
    return list(qs.order_by('-created_at')[offset:offset+limit])


def get_pending_events_by_tenant_batch(
    limit_per_tenant: int = 50, max_tenants: Optional[int] = None
) -> Dict[str, List[OutboxEvent]]:
    """Fetch pending events grouped by tenant.
    
    Enables per-tenant batch processing for the outbox worker.
    """
    # Get distinct tenant IDs with pending events
    tenant_ids = (
        OutboxEvent.objects
        .filter(status='pending')
        .values_list('tenant_id', flat=True)
        .distinct()
    )
    
    if max_tenants:
        tenant_ids = list(tenant_ids)[:max_tenants]
    
    # If no tenants found, check for NULL tenant_id events
    if not tenant_ids:
        null_count = OutboxEvent.objects.filter(
            status='pending',
            tenant_id__isnull=True
        ).count()
        if null_count > 0:
            tenant_ids = [None]
    
    # Fetch events for each tenant
    results = {}
    for tenant_id in tenant_ids:
        if tenant_id is None:
            qs = OutboxEvent.objects.filter(status='pending', tenant_id__isnull=True)
        else:
            qs = OutboxEvent.objects.filter(status='pending', tenant_id=tenant_id)
        
        events = list(qs.order_by('created_at')[:limit_per_tenant])
        if events:
            tenant_label = tenant_id or "default"
            results[tenant_label] = events
    
    return results


def get_pending_count(tenant_id: Optional[str] = None) -> int:
    """Return the number of pending outbox events.
    
    If tenant_id is provided, the count is restricted to that tenant.
    """
    qs = OutboxEvent.objects.filter(status='pending')
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    return qs.count()


def get_pending_counts_by_tenant() -> dict[str, int]:
    """Return the current pending event count per tenant."""
    counts = (
        OutboxEvent.objects
        .filter(status='pending')
        .values('tenant_id')
        .annotate(count=Count('id'))
    )
    return {row['tenant_id'] or 'default': row['count'] for row in counts}


# Replay functions - Extracted to somabrain/db/outbox_replay.py
# Re-export for backward compatibility


# Journal Integration Functions - Extracted to somabrain/db/outbox_journal.py
# Re-export for backward compatibility