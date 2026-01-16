"""Memory Admin API - Django Ninja Version

Migrated from FastAPI to Django Ninja.
Administrative endpoints for memory system management.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Any, Dict
from ninja import Router, Query
from django.http import HttpRequest
from ninja.errors import HttpError

from somabrain.api.auth import admin_auth
from somabrain.auth import require_admin_auth
from somabrain.api.memory.models import (
    AnnRebuildRequest,
    OutboxEventSummary,
    OutboxReplayRequest,
)
from somabrain.db import outbox as outbox_db

logger = logging.getLogger("somabrain.api.endpoints.memory_admin")

router = Router(tags=["memory-admin"])


def _get_tiered_registry():
    """Get the tiered memory registry singleton (lazy)."""
    # Import locally to avoid circular imports or early init
    try:
        from somabrain.services.tiered_memory_registry import TieredMemoryRegistry

        # We might need a global instance or create one.
        # The original code imported _TIERED_REGISTRY from somabrain.api.memory_api
        # We need to ensure we have access to it or instantiate it.
        # Since we are migrating, let's instantiate if not available or assume a singleton pattern.
        # However, TieredMemoryRegistry seems to be designed to be stateless/singleton-ish or rely on other singletons.
        return TieredMemoryRegistry()
    except ImportError:
        return None


@router.post("/rebuild-ann", auth=admin_auth)
def rebuild_ann_indexes(request: HttpRequest, payload: AnnRebuildRequest) -> Dict[str, Any]:
    """Admin: Rebuild ANN indexes."""
    require_admin_auth(request, getattr(request, "cfg", None))

    registry = _get_tiered_registry()
    if not registry:
        raise HttpError(503, "Tiered registry not available")

    results = registry.rebuild(payload.tenant, namespace=payload.namespace)
    return {"ok": True, "results": results}


@router.get("/outbox", response=List[OutboxEventSummary], auth=admin_auth)
def list_outbox_events(
    request: HttpRequest,
    status: str = Query("failed", description="Outbox status filter"),
    tenant: Optional[str] = Query(None, description="Optional tenant filter"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Admin: List outbox events."""
    require_admin_auth(request, getattr(request, "cfg", None))

    try:
        events = outbox_db.list_events_by_status(
            status=status, tenant_id=tenant, limit=limit, offset=offset
        )
    except ValueError as exc:
        raise HttpError(400, str(exc))

    summaries: List[OutboxEventSummary] = []
    for ev in events:
        # Django usage: created_at is datetime
        created_ts = ev.created_at.timestamp() if ev.created_at else 0.0
        summaries.append(
            OutboxEventSummary(
                id=int(ev.id),
                tenant_id=ev.tenant_id,
                topic=ev.topic,
                status=ev.status,
                retries=int(ev.retries or 0),
                created_at=float(created_ts),
                dedupe_key=str(ev.dedupe_key),
                last_error=ev.last_error,
                # payload in Django/JSONField is typically a dict already
                payload=ev.payload if isinstance(ev.payload, dict) else {},
            )
        )
    return summaries


@router.post("/outbox/replay", auth=admin_auth)
def replay_outbox_events(request: HttpRequest, payload: OutboxReplayRequest) -> Dict[str, Any]:
    """Admin: Replay outbox events."""
    require_admin_auth(request, getattr(request, "cfg", None))

    try:
        updated = outbox_db.mark_events_for_replay(payload.ids)
    except Exception as exc:
        raise HttpError(500, f"Replay failed: {exc}")

    return {"ok": True, "updated": int(updated)}
