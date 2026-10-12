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
from somabrain.math.contracts import OUTBOX_BACKPRESSURE_THRESHOLD
from somabrain.settings.resolve import UnconfiguredServiceError, require_tenant

logger = logging.getLogger(__name__)

VALID_OUTBOX_STATUSES = {"pending", "claimed", "sent", "failed"}


def claim_lease_seconds() -> int:
    """Drain lease length from settings (not a call-site constant)."""
    from somabrain.settings.resolve import require_setting

    return int(require_setting("OUTBOX_CLAIM_LEASE_SECONDS"))

# Memory operation topics per Task 10.1
# V5 FIX: ghost topics with no producers deleted (memory.delete,
# graph.delete_link, wm.persist, wm.evict). Implement or delete — no stubs.
MEMORY_TOPICS: dict[str, str] = {
    "memory.store": "Store memory to SFM",
    "memory.bulk_store": "Bulk store memories to SFM",
    "graph.link": "Create graph link in SFM",
    "wm.promote": "Promote WM item to LTM",
}

# Backpressure threshold per E2.5 — single source math/contracts.py


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


_BACKPRESSURE_COUNT_CACHE: dict[str, tuple[float, int]] = {}
_BACKPRESSURE_COUNT_TTL_S = 1.0


def check_backpressure(tenant_id: str | None = None) -> bool:
    """True when pending count is at/over the outbox threshold (E2.5).

    The pending COUNT is cached for a short window: a million-txn accept path
    cannot pay a full-table COUNT on every write. A 1s stale count only
    delays backpressure by one second — it never invents capacity that does
    not exist once the threshold is actually crossed.
    """
    import time as _time

    key = tenant_id or ""
    now = _time.monotonic()
    hit = _BACKPRESSURE_COUNT_CACHE.get(key)
    if hit is not None and (now - hit[0]) < _BACKPRESSURE_COUNT_TTL_S:
        pending = hit[1]
    else:
        pending = get_pending_count(tenant_id=tenant_id)
        _BACKPRESSURE_COUNT_CACHE[key] = (now, pending)
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


def mark_events_sent_bulk(event_ids: Sequence[int]) -> int:
    """Mark many outbox events sent in one statement (million-txn drain)."""
    ids = [int(i) for i in event_ids]
    if not ids:
        return 0
    return int(
        OutboxEvent.objects.filter(
            id__in=ids, status__in=("pending", "claimed", "failed")
        ).update(status="sent", claim_expires_at=None)
    )


def mark_events_failed_bulk(
    errors: Sequence[tuple[int, str]], *, max_retries: int
) -> int:
    """Release failed claims: bump retries, escalate past *max_retries*.

    Returns the number of rows escalated to terminal ``failed``. Rows under
    the cap return to ``pending`` so the next drain cycle can reclaim them
    (T-6 replay). Deduplicates event ids.

    Permanent HTTP 4xx (schema/tenant/auth) is terminal immediately — it
    will never succeed on retry. Only transient 5xx/timeouts retry.
    """
    from django.db.models import F

    seen: set[int] = set()
    retry_ids: list[int] = []
    dead_ids: list[int] = []
    for event_id, error in errors:
        eid = int(event_id)
        if eid in seen:
            continue
        seen.add(eid)
        if error:
            OutboxEvent.objects.filter(id=eid).update(last_error=error[:1000])
        if _is_permanent_client_error(error):
            dead_ids.append(eid)
        else:
            retry_ids.append(eid)
    if dead_ids:
        OutboxEvent.objects.filter(id__in=dead_ids).update(
            status="failed", claim_expires_at=None
        )
    if not retry_ids:
        return len(dead_ids)
    # Increment attempts first, then escalate any that crossed the cap.
    OutboxEvent.objects.filter(id__in=retry_ids).update(retries=F("retries") + 1)
    escalated = int(
        OutboxEvent.objects.filter(
            id__in=retry_ids, retries__gte=max_retries
        ).update(status="failed", claim_expires_at=None)
    )
    OutboxEvent.objects.filter(
        id__in=retry_ids, status="claimed"
    ).update(status="pending", claim_expires_at=None)
    return escalated + len(dead_ids)


def _is_permanent_client_error(error: str | None) -> bool:
    """True when the send error is a permanent HTTP 4xx (never retryable).

    Transient failures (timeouts, connection resets, 5xx, 429) return False
    so the row goes back to ``pending`` for T-6 replay.
    """
    if not error:
        return False
    text = str(error).lower()
    # Transient first: 5xx / 429 / timeouts always retry.
    if any(tok in text for tok in ("502", "503", "504", "429", "timeout", "timed out")):
        return False
    return any(
        tok in text
        for tok in (
            "400",
            "401",
            "403",
            "404",
            "409",
            "422",
            "unauthorized",
            "forbidden",
            "not found",
            "validation",
            "unprocessable",
            "conflict",
        )
    )


def reclaim_expired_claims(now=None) -> int:
    """Return expired ``claimed`` rows to ``pending`` (crash-safe leases)."""
    from django.utils import timezone

    moment = now or timezone.now()
    return int(
        OutboxEvent.objects.filter(
            status="claimed", claim_expires_at__lte=moment
        ).update(status="pending", claim_expires_at=None)
    )


def claim_pending_events(limit: int) -> list["OutboxEvent"]:
    """Claim drainable rows for this worker with a **lease**.

    Multi-replica protocol:
    1. Reclaim expired leases (crashed publishers).
    2. ``SELECT … FOR UPDATE SKIP LOCKED`` a disjoint slice.
    3. Stamp ``status=claimed`` + ``claim_expires_at`` **before** leaving the
       transaction so a concurrent publisher cannot take the same rows after
       the lock is released (SFM I/O runs outside any DB transaction).
    """
    from datetime import timedelta

    from django.utils import timezone

    if limit <= 0:
        return []
    reclaim_expired_claims()
    now = timezone.now()
    lease_until = now + timedelta(seconds=claim_lease_seconds())
    with transaction.atomic():
        rows = list(
            OutboxEvent.objects.select_for_update(skip_locked=True, of=("self",))
            .filter(status__in=("pending", "failed"), claim_expires_at__isnull=True)
            .order_by("created_at")[:limit]
        )
        if not rows:
            return []
        ids = [int(r.id) for r in rows]
        OutboxEvent.objects.filter(id__in=ids).update(
            status="claimed", claim_expires_at=lease_until
        )
        for row in rows:
            row.status = "claimed"
            row.claim_expires_at = lease_until
        return rows


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

    # T-6: the OutboxEvent row IS the durable accept. The local journal is a
    # redundancy copy — append it outside the insert path so a slow journal
    # rotate/fsync cannot sit on the million-txn accept latency budget.
    try:
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
    except Exception as exc:  # noqa: BLE001 — journal is not the durability gate
        logger.warning("outbox journal append failed (row is durable): %s", exc)

    return event


def get_pending_events(
    limit: int = 100, tenant_id: str | None = None
) -> list[OutboxEvent]:
    """Fetch a batch of drainable events (pending + failed) from the outbox.

    Uses the optimized index ix_outbox_status_tenant_created for efficient queries.
    Failed rows are retried on the next drain (T-6 replay covers both).
    """
    qs = OutboxEvent.objects.filter(status__in=("pending", "failed"))
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
    # Get distinct tenant IDs with drainable events (pending + failed).
    # A ``failed`` row is not a dead end: the next drain cycle retries it
    # (T-6 replay covers pending and failed).
    tenant_ids = list(
        OutboxEvent.objects.filter(status__in=("pending", "failed"))
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
        qs = OutboxEvent.objects.filter(
            status__in=("pending", "failed"), tenant_id=tenant_id
        )
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
