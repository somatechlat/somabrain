"""
Journal integration for the transactional outbox - Django ORM version.

Extracted from somabrain/db/outbox.py per vibe-compliance-audit spec.
Provides functions for integrating the local journal with the database outbox.

Thread Safety:
    These functions use the journal singleton which handles its own thread safety.
    Django ORM operations are thread-safe when wrapped in @transaction.atomic.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from django.db import transaction

from somabrain.journal import JournalEvent, get_journal

logger = logging.getLogger(__name__)


def get_journal_events(
    tenant_id: Optional[str] = None,
    status: Optional[str] = None,
    topic: Optional[str] = None,
    limit: Optional[int] = None,
    since: Optional[datetime] = None,
) -> List[JournalEvent]:
    """Get events from the local journal with filtering.

    Args:
        tenant_id: Optional tenant ID to filter by
        status: Optional status to filter by (pending|sent|failed)
        topic: Optional topic to filter by
        limit: Maximum number of events to return
        since: Only return events after this datetime

    Returns:
        List of journal events
    """
    try:
        journal = get_journal()
        return journal.read_events(
            tenant_id=tenant_id, status=status, topic=topic, limit=limit, since=since
        )
    except Exception as e:
        logger.error(f"Failed to read from journal: {e}")
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

    Args:
        tenant_id: Optional tenant ID to filter events
        limit: Maximum number of events to replay
        mark_processed: Whether to mark replayed events as processed in journal

    Returns:
        Number of events successfully replayed
    """
    # Import here to avoid circular dependency
    from somabrain.db.outbox import enqueue_event

    journal = get_journal()

    # Get pending events from journal
    events = journal.read_events(tenant_id=tenant_id, status="pending", limit=limit)

    if not events:
        return 0

    replayed_count = 0
    event_ids = []

    # Replay events to database outbox
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
            logger.error(f"Failed to replay journal event {event.id} to database: {e}")
            continue

    # Mark replayed events as processed in journal
    if mark_processed and event_ids:
        try:
            journal.mark_events_sent(event_ids)
        except Exception as e:
            logger.warning(f"Failed to mark journal events as processed: {e}")

    return replayed_count


def get_journal_stats() -> Dict[str, Any]:
    """Get statistics about the local journal.

    Returns:
        Dictionary with journal statistics
    """
    try:
        journal = get_journal()
        return journal.get_stats()
    except Exception as e:
        logger.error(f"Failed to get journal stats: {e}")
        return {"error": str(e)}


def cleanup_journal() -> Dict[str, Any]:
    """Clean up the local journal by removing old files.

    Returns:
        Dictionary with cleanup results
    """
    try:
        journal = get_journal()
        journal._cleanup_old_files()
        return {"success": True, "message": "Journal cleanup completed"}
    except Exception as e:
        logger.error(f"Failed to clean up journal: {e}")
        return {"success": False, "error": str(e)}
