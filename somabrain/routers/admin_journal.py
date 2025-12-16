"""Admin Journal Router
=====================

Admin endpoints for journal management.
All endpoints require admin authentication.

Extracted from somabrain/routers/admin.py per vibe-compliance-audit spec.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from common.config.settings import settings
from somabrain.auth import require_admin_auth
from somabrain.db.outbox import (
    get_journal_events,
    replay_journal_events,
    get_journal_stats,
    cleanup_journal,
)
from somabrain.journal import init_journal, JournalConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/journal", tags=["admin", "journal"])


def _admin_guard_dep(request: Request):
    """FastAPI dependency wrapper for admin auth."""
    return require_admin_auth(request, settings)


@router.get("/stats", dependencies=[Depends(_admin_guard_dep)])
async def admin_get_journal_stats():
    """Get statistics about the local journal."""
    try:
        stats = get_journal_stats()
        return {"success": True, "data": stats}
    except Exception as e:
        logger.error(f"Failed to get journal stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/events", dependencies=[Depends(_admin_guard_dep)])
async def admin_list_journal_events(
    tenant_id: Optional[str] = Query(None, description="Filter by tenant ID"),
    status: Optional[str] = Query(None, description="Filter by status (pending|sent|failed)"),
    topic: Optional[str] = Query(None, description="Filter by topic"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of events to return"),
    since: Optional[str] = Query(None, description="Only events after this ISO datetime"),
):
    """List journal events with filtering options."""
    try:
        since_dt = None
        if since:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))

        events = get_journal_events(
            tenant_id=tenant_id,
            status=status,
            topic=topic,
            limit=limit,
            since=since_dt,
        )

        return {
            "success": True,
            "data": {
                "events": [
                    {
                        "id": ev.id,
                        "topic": ev.topic,
                        "tenant_id": ev.tenant_id,
                        "status": ev.status,
                        "retries": ev.retries,
                        "last_error": ev.last_error,
                        "timestamp": ev.timestamp.isoformat(),
                    }
                    for ev in events
                ],
                "count": len(events),
            },
        }
    except Exception as e:
        logger.error(f"Failed to list journal events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/replay", dependencies=[Depends(_admin_guard_dep)])
async def admin_replay_journal_events(
    tenant_id: Optional[str] = Query(None, description="Filter by tenant ID"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of events to replay"),
    mark_processed: bool = Query(True, description="Mark replayed events as processed"),
):
    """Replay journal events to the database outbox."""
    try:
        replayed = replay_journal_events(
            tenant_id=tenant_id, limit=limit, mark_processed=mark_processed
        )

        return {
            "success": True,
            "data": {
                "replayed_count": replayed,
                "message": f"Successfully replayed {replayed} events from journal to database",
            },
        }
    except Exception as e:
        logger.error(f"Failed to replay journal events: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup", dependencies=[Depends(_admin_guard_dep)])
async def admin_cleanup_journal():
    """Clean up old journal files based on retention policy."""
    try:
        result = cleanup_journal()
        return {"success": True, "data": result}
    except Exception as e:
        logger.error(f"Failed to cleanup journal: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/init", dependencies=[Depends(_admin_guard_dep)])
async def admin_init_journal(
    journal_dir: Optional[str] = Query(None, description="Journal directory path"),
    max_file_size: Optional[int] = Query(None, description="Max file size in bytes"),
    max_files: Optional[int] = Query(None, description="Max number of files"),
    retention_days: Optional[int] = Query(None, description="Retention period in days"),
):
    """Initialize or reconfigure the journal."""
    try:
        # Get current config or create new one
        config = JournalConfig.from_env()

        # Update with provided parameters
        if journal_dir is not None:
            config.journal_dir = journal_dir
        if max_file_size is not None:
            config.max_file_size = max_file_size
        if max_files is not None:
            config.max_files = max_files
        if retention_days is not None:
            config.retention_days = retention_days

        # Initialize journal with new config
        journal = init_journal(config)

        return {
            "success": True,
            "data": {
                "config": {
                    "journal_dir": config.journal_dir,
                    "max_file_size": config.max_file_size,
                    "max_files": config.max_files,
                    "retention_days": config.retention_days,
                },
                "stats": journal.get_stats(),
            },
        }
    except Exception as e:
        logger.error(f"Failed to initialize journal: {e}")
        raise HTTPException(status_code=500, detail=str(e))
