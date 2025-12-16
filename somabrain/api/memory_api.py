"""Memory API (No-Kong edition).

Provides FastAPI endpoints for governed memory read/write operations against the
real runtime singletons (working memory + multi-tenant memory pool). The
endpoints are thin wrappers that keep all logic inside the production services
so they stay in sync with the main application surface.

Architecture:
    Uses DI container for state management. The RecallSessionStore class
    encapsulates session management with TTL-based expiration, registered
    with the container for explicit lifecycle management.

Module Organization:
    - models.py: Pydantic request/response models
    - helpers.py: Helper functions for payload composition and retrieval
    - session.py: Recall session store management
    - remember.py: Remember (write) endpoints
    - recall.py: Core recall implementation
    - admin.py: Admin endpoints (ANN rebuild, outbox management)
    - This file: Router setup and recall endpoints using retrieval pipeline
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional, Annotated

from fastapi import APIRouter, HTTPException, Query, Request, Body

# Import Pydantic models from extracted module
from somabrain.api.memory.models import (
    MemoryRecallRequest,
    MemoryRecallItem,
    MemoryRecallResponse,
    MemoryMetricsResponse,
    MemoryRecallSessionResponse,
)

# Import helper functions from extracted module
from somabrain.api.memory.helpers import (
    _get_wm,
    _get_memory_pool,
    _resolve_namespace,
    _map_retrieval_to_memory_items as _map_retrieval_items_helper,
    _coerce_to_retrieval_request as _coerce_request_helper,
)

# Import session store from extracted module
from somabrain.api.memory.session import get_recall_session_store

# Import remember endpoints factory
from somabrain.api.memory.remember import create_remember_endpoints

# Import admin router
from somabrain.api.memory.admin import router as admin_router

from somabrain.metrics import record_memory_snapshot
from somabrain.services.memory_service import MemoryService
from somabrain.services.tiered_memory_registry import TieredMemoryRegistry
from somabrain.runtime.config_runtime import (
    ensure_config_dispatcher,
    ensure_supervisor_worker,
    register_config_listener,
)

# Unified configuration
from common.config.settings import settings

# Auth and tenant resolution
from somabrain.auth import require_auth
from somabrain.schemas import RetrievalRequest
from somabrain.tenant import get_tenant as get_tenant_async

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/memory", tags=["memory"])

# Module-level tiered registry
_TIERED_REGISTRY = TieredMemoryRegistry()


def _handle_config_event(event) -> None:
    """Handle config events for tiered registry."""
    metrics = _TIERED_REGISTRY.apply_effective_config(event)
    if not metrics:
        return
    tenant = event.tenant or "unknown"
    namespace = event.namespace or "default"
    try:
        record_memory_snapshot(
            tenant,
            namespace,
            eta=metrics.get("eta"),
            sparsity=metrics.get("sparsity"),
            config_version=event.version,
        )
    except Exception as e:
        logger.debug("Failed to record memory snapshot for config event: %s", e)


register_config_listener(_handle_config_event)


async def _ensure_config_runtime_started() -> None:
    """Ensure config runtime is started."""
    await ensure_config_dispatcher()
    await ensure_supervisor_worker()


def _tiered_enabled() -> bool:
    """Check if tiered memory feature is enabled."""
    from somabrain.modes import feature_enabled

    return feature_enabled("tiered_memory")


def _prune_sessions() -> None:
    """Prune expired recall sessions from the store."""
    get_recall_session_store().prune()


# ============================================================================
# INCLUDE REMEMBER ENDPOINTS FROM EXTRACTED MODULE
# ============================================================================

# Create and include remember endpoints with the tiered registry
_remember_router = create_remember_endpoints(_TIERED_REGISTRY)
router.include_router(_remember_router)


# ============================================================================
# RECALL ENDPOINTS
# ============================================================================


def _map_retrieval_to_memory_items(candidates: List[dict]) -> List[MemoryRecallItem]:
    """Map retrieval candidates to MemoryRecallItem instances."""
    return _map_retrieval_items_helper(candidates, MemoryRecallItem)


def _coerce_to_retrieval_request(obj: object, default_top_k: int = 10) -> RetrievalRequest:
    """Coerce various input types to a RetrievalRequest."""
    return _coerce_request_helper(obj, default_top_k, RetrievalRequest, MemoryRecallRequest)


@router.post("/recall", response_model=MemoryRecallResponse)
async def recall_memory(
    payload: Annotated[Any, Body(...)], request: Request
) -> MemoryRecallResponse:
    """Unified recall endpoint backed by the retrieval pipeline."""
    await _ensure_config_runtime_started()
    cfg = settings
    ctx = await get_tenant_async(request, cfg.namespace)
    require_auth(request, cfg)
    from somabrain.infrastructure.cb_registry import get_cb

    cb = get_cb()
    degrade_readonly = bool(getattr(cfg, "memory_degrade_readonly", False))
    ret_req = _coerce_to_retrieval_request(payload, default_top_k=10)

    circuit_open = cb.is_open(ctx.tenant_id) or cb.should_attempt_reset(ctx.tenant_id)
    degraded = False
    if circuit_open:
        degraded = True
        ret_req.retrievers = ["wm"]
        ret_req.persist = False
        ret_req.layer = "wm"
        if degrade_readonly:
            ret_req.retrievers = ["wm"]

    t0 = time.perf_counter()
    from somabrain.services.retrieval_pipeline import run_retrieval_pipeline

    ret_resp = await run_retrieval_pipeline(
        ret_req,
        ctx=ctx,
        universe=ret_req.universe,
        trace_id=request.headers.get("X-Request-ID"),
    )
    dt_ms = round((time.perf_counter() - t0) * 1000.0, 3)

    ret_dict = ret_resp.dict() if hasattr(ret_resp, "dict") else ret_resp
    cands = ret_dict.get("candidates") or []
    items = _map_retrieval_to_memory_items(cands)

    wm_hits = sum(1 for it in items if it.layer == "wm")
    ltm_hits = sum(1 for it in items if it.layer != "wm")

    try:
        from somabrain import metrics as M

        M.RECALL_REQUESTS.labels(namespace=ctx.namespace).inc()
    except Exception:
        pass

    return MemoryRecallResponse(
        tenant=ctx.tenant_id,
        namespace=ctx.namespace,
        results=items,
        wm_hits=wm_hits,
        ltm_hits=ltm_hits,
        duration_ms=dt_ms,
        session_id=str(ret_dict.get("session_coord") or ""),
        scoring_mode=None,
        chunk_index=0,
        has_more=False,
        total_results=len(items),
        chunk_size=None,
        conversation_id=None,
        degraded=degraded,
    )


@router.post("/recall/stream", response_model=MemoryRecallResponse)
async def recall_memory_stream(
    payload: Annotated[Any, Body(...)], request: Request
) -> MemoryRecallResponse:
    """Streaming recall with chunking."""
    ret_req = _coerce_to_retrieval_request(payload, default_top_k=10)
    chunk_size = min(max(1, int(ret_req.top_k)), 5)
    base = await recall_memory(payload, request)
    start_index = 0
    end_index = min(len(base.results), chunk_size)
    base.results = base.results[start_index:end_index]
    base.has_more = end_index < base.total_results
    base.chunk_index = 0
    base.chunk_size = chunk_size
    return base


@router.get("/context/{session_id}", response_model=MemoryRecallSessionResponse)
async def get_recall_session(session_id: str) -> MemoryRecallSessionResponse:
    """Get a stored recall session by ID."""
    _prune_sessions()
    state = get_recall_session_store().get(session_id)
    if state is None:
        raise HTTPException(status_code=404, detail="session not found or expired")
    results = [MemoryRecallItem(**item) for item in state.get("results", [])]
    return MemoryRecallSessionResponse(
        session_id=session_id,
        tenant=state.get("tenant", ""),
        namespace=state.get("namespace", ""),
        scoring_mode=state.get("scoring_mode"),
        conversation_id=state.get("conversation_id"),
        created_at=state.get("created_at", 0.0),
        results=results,
    )


# ============================================================================
# METRICS ENDPOINT
# ============================================================================


@router.get("/metrics", response_model=MemoryMetricsResponse)
async def memory_metrics(
    tenant: str = Query(..., min_length=1),
    namespace: str = Query(..., min_length=1),
) -> MemoryMetricsResponse:
    """Get memory metrics for a tenant/namespace."""
    await _ensure_config_runtime_started()
    pool = _get_memory_pool()
    wm = _get_wm()
    resolved_ns = _resolve_namespace(tenant, namespace)
    memsvc = MemoryService(pool, resolved_ns)
    memsvc._reset_circuit_if_needed()

    try:
        wm_items = len(wm.items(tenant))
    except Exception:
        wm_items = 0

    try:
        record_memory_snapshot(tenant, namespace, items=wm_items)
    except Exception:
        pass

    return MemoryMetricsResponse(
        tenant=tenant,
        namespace=namespace,
        wm_items=wm_items,
        circuit_open=memsvc._is_circuit_open(),
    )


# ============================================================================
# INCLUDE ADMIN ROUTER
# ============================================================================

# Admin endpoints are in a separate module with /admin prefix
# Combined with main router's /memory prefix = /memory/admin/*
router.include_router(admin_router)
