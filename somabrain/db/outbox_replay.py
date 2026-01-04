"""
Replay functions for the transactional outbox - Django ORM version.

Extracted from somabrain/db/outbox.py per vibe-compliance-audit spec.
Provides functions for replaying failed events and tenant-specific replay.

Thread Safety:
    Django QuerySets are thread-safe. @transaction.atomic ensures ACID properties.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from django.db import transaction
from django.db.models import Count

from somabrain.models import OutboxEvent
from somabrain.metrics import report_outbox_replayed

logger = logging.getLogger(__name__)

VALID_OUTBOX_STATUSES = {"pending", "sent", "failed"}


@transaction.atomic
def mark_events_for_replay(limit: int = 100, tenant_id: Optional[str] = None) -> int:
    """Mark failed events for replay by setting their status back to 'pending'.
    
    Args:
        limit: Maximum number of events to mark for replay
        tenant_id: Specific tenant to replay (None for all tenants)
    
    Returns:
        Number of events marked for replay
    """
    qs = OutboxEvent.objects.filter(status='failed')
    if tenant_id:
        qs = qs.filter(tenant_id=tenant_id)
    
    events = list(qs.order_by('created_at')[:limit])
    count = 0
    
    for ev in events:
        ev.status = 'pending'
        ev.retries = 0
        ev.last_error = None
        ev.save()
        count += 1
    
    # Report metrics
    tenant_label = tenant_id or "default"
    if report_outbox_replayed is not None and count > 0:
        try:
            report_outbox_replayed(tenant_label, count)
        except Exception as exc:
            logger.debug(
                "Failed to report outbox replayed for tenant=%s: %s",
                tenant_label,
                exc,
            )
    
    return count


@transaction.atomic
def mark_tenant_events_for_replay(
    tenant_id: str, limit: int = 100, status: str = "failed"
) -> int:
    """Mark events for a specific tenant for replay.
    
    Args:
        tenant_id: The tenant ID to replay events for
        limit: Maximum number of events to replay
        status: Status of events to replay (failed or sent)
    
    Returns:
        Number of events marked for replay
    """
    if status not in VALID_OUTBOX_STATUSES:
        raise ValueError(f"Invalid outbox status: {status}")
    
    limit = max(1, min(int(limit), 1000))
    
    events = list(
        OutboxEvent.objects
        .filter(tenant_id=tenant_id, status=status)
        .order_by('created_at')[:limit]
    )
    
    count = 0
    for ev in events:
        ev.status = 'pending'
        ev.retries = 0
        ev.last_error = None
        ev.save()
        count += 1
    
    # Report metrics
    if report_outbox_replayed is not None and count > 0:
        try:
            report_outbox_replayed(tenant_id, count)
        except Exception as exc:
            logger.debug(
                "Failed to report outbox replayed for tenant=%s: %s", tenant_id, exc
            )
    
    return count


def list_tenant_events(
    tenant_id: str,
    status: str = "pending",
    topic_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> List[OutboxEvent]:
    """List outbox events for a specific tenant with filtering options.
    
    Args:
        tenant_id: The tenant ID to get events for
        status: Filter events by status (pending|failed|sent)
        topic_filter: Optional topic pattern to filter events
        limit: Maximum number of events to return
        offset: Offset for pagination
    
    Returns:
        List of outbox events
    """
    if status not in VALID_OUTBOX_STATUSES:
        raise ValueError(f"Invalid outbox status: {status}")
    
    limit = max(1, min(int(limit), 1000))
    offset = max(0, int(offset))
    
    qs = OutboxEvent.objects.filter(tenant_id=tenant_id, status=status)
    
    if topic_filter:
        qs = qs.filter(topic__icontains=topic_filter)
    
    return list(qs.order_by('-created_at')[offset:offset+limit])


def get_failed_counts_by_tenant() -> Dict[str, int]:
    """Get failed event counts per tenant.
    
    Returns:
        Dict mapping tenant_id to failed event count
    """
    counts = (
        OutboxEvent.objects
        .filter(status='failed')
        .values('tenant_id')
        .annotate(count=Count('id'))
    )
    return {row['tenant_id'] or 'default': row['count'] for row in counts}


def get_sent_counts_by_tenant() -> Dict[str, int]:
    """Get sent event counts per tenant.
    
    Returns:
        Dict mapping tenant_id to sent event count
    """
    counts = (
        OutboxEvent.objects
        .filter(status='sent')
        .values('tenant_id')
        .annotate(count=Count('id'))
    )
    return {row['tenant_id'] or 'default': row['count'] for row in counts}