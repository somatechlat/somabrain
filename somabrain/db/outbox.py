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

import logging
from typing import Any, Sequence

from django.db import transaction
from django.db.models import Count

from somabrain.admin.core.models import OutboxEvent
from somabrain.journal import JournalEvent, get_journal
from somabrain.settings.resolve import UnconfiguredServiceError, require_tenant

logger = logging.getLogger(__name__)

VALID_OUTBOX_STATUSES = {"pending", "sent", "failed"}

# Memory operation topics per Task 10.1
MEMORY_TOPICS: dict[str, str] = {
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
    ) -> None:
        """Initialize the instance."""

        self.pending_count = pending_count
        self.threshold = threshold
        super().__init__(
            f"Outbox backpressure: {pending_count} pending events exceeds threshold {threshold}"
        )


def _coord_to_str(coord: tuple[float, float, float] | list[float] | str) -> str:
    """Canonical coordinate string — the seam's ``f"{x},{y},{z}"`` float repr.

    Must match ``memory_contract.coord_from_key_material`` /
    ``make_coord`` so both sides of the seam form the same identity.
    """
    if isinstance(coord, str):
        return coord.strip()
    return f"{coord[0]},{coord[1]},{coord[2]}"


def _idempotency_key(
    operation: str,
    coord: tuple[float, float, float] | list[float] | str | None = None,
    tenant: str | None = None,
    extra: str | None = None,
) -> str:
    """Return the one idempotency key: ``mem:{coord}`` (INVARIANTS §3.3).

    "The idempotency key MUST be ``mem:{coord}`` — not a UUID (a random
    suffix makes the outbox multiply memories)."

    No operation prefix, no tenant mix-in, no extra suffix. The arguments are
    kept for call-site compatibility but do NOT change the identity — a key
    that varies with request id or tenant would let replays multiply rows.

    Fails closed when ``coord`` is absent: a memory event with no coordinate
    has no stable identity and must not fall back to a random key.
    """
    if coord is None:
        raise ValueError(
            "idempotency key requires a coordinate (INVARIANTS §3.3: "
            "mem:{coord}); a missing coord must not fall back to a random key"
        )
    return f"mem:{_coord_to_str(coord)}"


def check_backpressure(tenant_id: str | None = None) -> bool:
    """Check if outbox is under backpressure.

    Per Requirement E2.5: Returns True if pending count exceeds threshold.
    """
    pending = get_pending_count(tenant_id=tenant_id)
    return pending >= OUTBOX_BACKPRESSURE_THRESHOLD


def enqueue_memory_event(
    topic: str,
    payload: dict[str, Any],
    tenant_id: str,
    coord: tuple[float, float, float] | None = None,
    extra_key: str | None = None,
    check_backpressure_flag: bool = True,
) -> int:
    """Enqueue a memory operation event and return the OutboxEvent primary key.

    Per Requirements E2.1-E2.5.

    Returns the integer PK required by :func:`mark_event_sent`. The
    idempotency ``dedupe_key`` is stored on the row and can be read via
    :func:`get_event_by_dedupe_key` if needed.
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
    event = enqueue_event(
        topic=topic,
        payload=payload,
        dedupe_key=dedupe_key,
        tenant_id=tenant_id,
    )

    logger.debug(
        f"Enqueued memory event: topic={topic}, tenant={tenant_id}, "
        f"dedupe_key={dedupe_key}, event_id={event.id}"
    )

    return int(event.id)


@transaction.atomic
def mark_event_sent(event_id: int) -> bool:
    """Mark an outbox event as sent.

    Per Requirement E2.2: Mark "sent" on success.
    """
    updated = OutboxEvent.objects.filter(id=event_id).update(status="sent")
    return updated > 0


@transaction.atomic
def mark_events_for_replay(event_ids: Sequence[int]) -> int:
    """Mark specific outbox events (by primary key) back to pending for replay.

    Args:
        event_ids: OutboxEvent primary keys to requeue.

    Returns:
        Number of rows updated.
    """
    ids = [int(i) for i in event_ids]
    if not ids:
        return 0
    updated = OutboxEvent.objects.filter(
        id__in=ids, status__in=["failed", "pending"]
    ).update(
        status="pending",
        retries=0,
        last_error=None,
    )
    return int(updated)


@transaction.atomic
def mark_event_failed(event_id: int, error: str) -> bool:
    """Mark an outbox event as failed with error message.

    Per Requirement E2.3: Remain "pending" for retry, but track failures.
    """
    from django.db.models import F

    updated = OutboxEvent.objects.filter(id=event_id).update(
        status="failed",
        last_error=error[:1000] if error else None,
        retries=F("retries") + 1,
    )
    return updated > 0


def get_event_by_dedupe_key(
    dedupe_key: str,
    tenant_id: str | None = None,
) -> OutboxEvent | None:
    """Get an outbox event by its deduplication key.

    Per Requirement E2.4: Used for duplicate detection.
    """
    qs = OutboxEvent.objects.filter(dedupe_key=dedupe_key)
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    return qs.first()


def is_duplicate_event(
    dedupe_key: str,
    tenant_id: str | None = None,
) -> bool:
    """Check if an event with this dedupe_key already exists.

    Per Requirement E2.4: Duplicate detection.
    """
    return get_event_by_dedupe_key(dedupe_key, tenant_id) is not None


@transaction.atomic
def enqueue_event(
    topic: str,
    payload: dict[str, Any],
    dedupe_key: str | None = None,
    tenant_id: str | None = None,
) -> OutboxEvent:
    """Enqueue a new event to the outbox.

    Returns the created OutboxEvent instance.

    T-5: ``tenant_id`` is required. A missing tenant is a missing identity at
    the write boundary — it raises rather than landing in a NULL-tenant row
    that a later batch would have to remap (AP-04).
    """
    tenant_id = require_tenant(tenant_id)
    if dedupe_key is None or not str(dedupe_key).strip():
        raise ValueError(
            "enqueue_event requires a non-empty dedupe_key; a UUID fallback "
            "is a multiplier (INVARIANTS §3.3)"
        )

    event = OutboxEvent.objects.create(
        topic=topic,
        payload=payload,
        dedupe_key=dedupe_key,
        tenant_id=tenant_id,
        status="pending",
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
    limit: int = 100, tenant_id: str | None = None
) -> list[OutboxEvent]:
    """Fetch a batch of pending events from the outbox.

    Uses the optimized index ix_outbox_status_tenant_created for efficient queries.
    """
    qs = OutboxEvent.objects.filter(status="pending")
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    # Order by created_at to ensure FIFO processing
    return list(qs.order_by("created_at")[:limit])


def list_events_by_status(
    status: str = "pending",
    tenant_id: str | None = None,
    topic_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[OutboxEvent]:
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

    return list(qs.order_by("-created_at")[offset : offset + limit])


def get_pending_events_by_tenant_batch(
    limit_per_tenant: int = 50, max_tenants: int | None = None
) -> dict[str, list[OutboxEvent]]:
    """Fetch pending events grouped by tenant.

    Enables per-tenant batch processing for the outbox worker.

    T-5: a pending event with no tenant is a corrupt partition boundary. It is
    never labelled ``"default"`` — the batch raises naming the missing tenant,
    so the poison row is visible instead of being published into a shared
    partition (AP-04).
    """
    # Get distinct tenant IDs with pending events
    tenant_ids = list(
        OutboxEvent.objects.filter(status="pending")
        .values_list("tenant_id", flat=True)
        .distinct()
    )

    if max_tenants:
        tenant_ids = tenant_ids[:max_tenants]

    missing = [t for t in tenant_ids if t is None or not str(t).strip()]
    if missing:
        raise UnconfiguredServiceError(
            f"outbox has {len(missing)} pending event(s) with a missing tenant_id; "
            "refusing to group them under a default tenant (T-5)."
        )

    # Fetch events for each tenant
    results = {}
    for tenant_id in tenant_ids:
        label = require_tenant(tenant_id)
        qs = OutboxEvent.objects.filter(status="pending", tenant_id=tenant_id)
        events = list(qs.order_by("created_at")[:limit_per_tenant])
        if events:
            results[label] = events

    return results


def get_pending_count(tenant_id: str | None = None) -> int:
    """Return the number of pending outbox events.

    If tenant_id is provided, the count is restricted to that tenant.
    """
    qs = OutboxEvent.objects.filter(status="pending")
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    return qs.count()


def get_pending_counts_by_tenant() -> dict[str, int]:
    """Return the current pending event count per tenant.

    T-5: a row with no tenant raises rather than being reported as tenant
    ``"default"`` — metrics must not invent a partition either.
    """
    counts = (
        OutboxEvent.objects.filter(status="pending")
        .values("tenant_id")
        .annotate(count=Count("id"))
    )
    result: dict[str, int] = {}
    for row in counts:
        label = require_tenant(row["tenant_id"])
        result[label] = row["count"]
    return result


# Replay functions - Extracted to somabrain/db/outbox_replay.py
# Re-export for backward compatibility


# Journal Integration Functions - Extracted to somabrain/db/outbox_journal.py
# Re-export for backward compatibility
