"""Memory Admin API endpoints.

Provides administrative endpoints for memory system management:
- ANN index rebuilding
- Outbox event management and replay
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from somabrain.api.memory.models import (
    AnnRebuildRequest,
    OutboxEventSummary,
    OutboxReplayRequest,
)
from somabrain.auth import require_admin_auth
from somabrain.db import outbox as outbox_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["memory-admin"])


async def _ensure_config_runtime_started() -> None:
    """Ensure config runtime is started."""
    from somabrain.runtime.config_runtime import (
        ensure_config_dispatcher,
        ensure_supervisor_worker,
    )

    await ensure_config_dispatcher()
    await ensure_supervisor_worker()


def _get_tiered_registry():
    """Get the tiered memory registry singleton."""
    from somabrain.api.memory_api import _TIERED_REGISTRY

    return _TIERED_REGISTRY


@router.post("/rebuild-ann")
async def rebuild_ann_indexes(payload: AnnRebuildRequest) -> Dict[str, Any]:
    """Admin: Rebuild ANN indexes."""
    await _ensure_config_runtime_started()
    registry = _get_tiered_registry()
    results = registry.rebuild(payload.tenant, namespace=payload.namespace)
    return {"ok": True, "results": results}


@router.get("/outbox", response_model=List[OutboxEventSummary])
async def list_outbox_events(
    request: Request,
    status: str = Query("failed", description="Outbox status filter"),
    tenant: Optional[str] = Query(None, description="Optional tenant filter"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> List[OutboxEventSummary]:
    """Admin: List outbox events."""
    cfg = getattr(request.app.state, "cfg", None)
    require_admin_auth(request, cfg)
    try:
        events = outbox_db.list_events_by_status(
            status=status, tenant_id=tenant, limit=limit, offset=offset
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    summaries: List[OutboxEventSummary] = []
    for ev in events:
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
                payload=ev.payload if isinstance(ev.payload, dict) else {},
            )
        )
    return summaries


@router.post("/outbox/replay")
async def replay_outbox_events(
    request: Request, payload: OutboxReplayRequest
) -> Dict[str, Any]:
    """Admin: Replay outbox events."""
    cfg = getattr(request.app.state, "cfg", None)
    require_admin_auth(request, cfg)
    try:
        updated = outbox_db.mark_events_for_replay(payload.ids)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Replay failed: {exc}") from exc
    return {"ok": True, "updated": int(updated)}
