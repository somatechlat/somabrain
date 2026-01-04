"""
Outbox cleanup and replay operations using Django ORM.

Migrated from SQLAlchemy to Django ORM.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from django.db import transaction
from django.db.models import Count

from somabrain.models import OutboxEvent
from somabrain.metrics import report_outbox_replayed
from somabrain.journal import get_journal, JournalEvent

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
        ev.status =  'pending'
        ev.retries = 0
        ev.last_error = None
        ev.save()
        count += 1
    
    # Report metrics
    tenant_label = tenant_id or "default"
    if report_outbox_replayed is not None and count > 0:
        try:
            report_outbox_replayed(tenant_label, count)
        except Exception:
            pass
    
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
        except Exception:
            pass
    
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
    """Get failed event counts per tenant."""
    counts = (
        OutboxEvent.objects
        .filter(status='failed')
        .values('tenant_id')
        .annotate(count=Count('id'))
    )
    return {row['tenant_id'] or 'default': row['count'] for row in counts}


def get_sent_counts_by_tenant() -> Dict[str, int]:
    """Get sent event counts per tenant."""
    counts = (
        OutboxEvent.objects
        .filter(status='sent')
        .values('tenant_id')
        .annotate(count=Count('id'))
    )
    return {row['tenant_id'] or 'default': row['count'] for row in counts}


# Journal Integration Functions

def get_journal_events(
    tenant_id: Optional[str] = None,
    status: Optional[str] = None,
    topic: Optional[str] = None,
    limit: Optional[int] = None,
    since: Optional[datetime] = None,
) -> List[JournalEvent]:
    """Get events from the local journal with filtering."""
    try:
        journal = get_journal()
        return journal.read_events(
            tenant_id=tenant_id, status=status, topic=topic, limit=limit, since=since
        )
    except Exception as e:
        import logging
        
        logging.getLogger(__name__).error(f"Failed to read from journal: {e}")
        return []


@transaction.atomic
def replay_journal_events(
    tenant_id: Optional[str] = None,
    limit: int = 100,
    mark_processed: bool = True,
) -> int:
    """Replay journal events to the database outbox.
    
    This function reads events from the local journal and enqueues them
    in the database outbox for processing by the outbox worker.
    """
    from somabrain.db.outbox import enqueue_event
    
    journal = get_journal()
    events = journal.read_events(tenant_id=tenant_id, status="pending", limit=limit)
    
    if not events:
        return 0
    
    replayed_count = 0
    event_ids = []
    
    for event in events:
        try:
            enqueue_event(
                topic=event.topic,
                payload=event.payload,
                dedupe_key=event.dedupe_key,
                tenant_id=event.tenant_id,
            )
            replayed_count += 1
            event_ids.append(event.id)
        
        except Exception as e:
            import logging
            
            logging.getLogger(__name__).error(
                f"Failed to replay journal event {event.id} to database: {e}"
            )
            continue
    
    if mark_processed and event_ids:
        try:
            journal.mark_events_sent(event_ids)
        except Exception as e:
            import logging
            
            logging.getLogger(__name__).warning(
                f"Failed to mark journal events as processed: {e}"
            )
    
    return replayed_count


def get_journal_stats() -> Dict[str, Any]:
    """Get statistics about the local journal."""
    try:
        journal = get_journal()
        return journal.get_stats()
    except Exception as e:
        import logging
        
        logging.getLogger(__name__).error(f"Failed to get journal stats: {e}")
        return {"error": str(e)}


def cleanup_journal() -> Dict[str, Any]:
    """Clean up the local journal by removing old files."""
    try:
        journal = get_journal()
        journal._cleanup_old_files()
        return {"success": True, "message": "Journal cleanup completed"}
    except Exception as e:
        import logging
        
        logging.getLogger(__name__).error(f"Failed to clean up journal: {e}")
        return {"success": False, "error": str(e)}