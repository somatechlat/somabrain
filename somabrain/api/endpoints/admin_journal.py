"""Admin Journal Router - Django Ninja Version

Migrated from FastAPI to Django Ninja.
Journal management endpoints for administrators.
"""

from __future__ import annotations

import logging
from typing import Optional
from ninja import Router
from django.http import HttpRequest
from ninja.errors import HttpError

from django.conf import settings
from django.conf import settings
from somabrain.schemas import JournalReplayRequest
from somabrain.api.auth import admin_auth
from somabrain.db import outbox_journal

logger = logging.getLogger("somabrain.api.endpoints.admin_journal")

router = Router(tags=["admin"])


@router.get("/journal/events", auth=admin_auth)
def list_journal_events(
    request: HttpRequest,
    limit: int = 100,
    offset: int = 0,
    tenant_id: Optional[str] = None,
):
    """List journal events with optional tenant filtering."""
    try:
        events = outbox_journal.list_journal_events(
            limit=limit,
            offset=offset,
            tenant_id=tenant_id,
        )
        return {
            "events": [
                {
                    "id": ev.id,
                    "tenant_id": ev.tenant_id,
                    "event_type": ev.event_type,
                    "payload": ev.payload,
                    "created_at": ev.created_at.isoformat() if ev.created_at else None,
                }
                for ev in events
            ],
            "count": len(events),
        }
    except Exception as exc:
        logger.error(f"Failed to list journal events: {exc}")
        raise HttpError(500, f"Failed to list journal events: {exc}")


@router.post("/journal/replay", auth=admin_auth)
def replay_journal_events(
    request: HttpRequest,
    body: JournalReplayRequest,
):
    """Replay journal events to outbox."""
    try:
        count = outbox_journal.replay_journal_events(
            event_ids=body.event_ids if hasattr(body, "event_ids") else [],
            tenant_id=body.tenant_id if hasattr(body, "tenant_id") else None,
        )
        
        logger.info(f"Replayed {count} journal events")
        
        return {
            "replayed": count,
            "success": True,
        }
    except Exception as exc:
        logger.error(f"Failed to replay journal events: {exc}")
        raise HttpError(500, f"Failed to replay journal events: {exc}")


@router.delete("/journal/cleanup", auth=admin_auth)
def cleanup_journal(
    request: HttpRequest,
    older_than_days: int = 30,
):
    """Clean up old journal events."""
    try:
        deleted_count = outbox_journal.cleanup_old_journal_events(
            older_than_days=older_than_days
        )
        
        logger.info(f"Cleaned up {deleted_count} old journal events (older than {older_than_days} days)")
        
        return {
            "deleted": deleted_count,
            "success": True,
        }
    except Exception as exc:
        logger.error(f"Failed to cleanup journal: {exc}")
        raise HttpError(500, f"Failed to cleanup journal: {exc}")
