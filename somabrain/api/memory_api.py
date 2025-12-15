"""Memory API (No-Kong edition).

Provides FastAPI endpoints for governed memory read/write operations against the
real runtime singletons (working memory + multi-tenant memory pool). The
endpoints are thin wrappers that keep all logic inside the production services
so they stay in sync with the main application surface.

Architecture:
    Uses DI container for state management. The RecallSessionStore class
    encapsulates session management with TTL-based expiration, registered
    with the container for explicit lifecycle management.
"""

from __future__ import annotations

import copy
import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Annotated

import numpy as np
from fastapi import APIRouter, HTTPException, Query, Request, Body

# Import Pydantic models from extracted module
from somabrain.api.memory.models import (
    MemorySignalFeedback,
    MemoryWriteRequest,
    MemoryWriteResponse,
    MemoryRecallRequest,
    MemoryRecallItem,
    MemoryRecallResponse,
    MemoryMetricsResponse,
    MemoryBatchWriteRequest,
    MemoryBatchWriteResult,
    MemoryBatchWriteResponse,
    MemoryRecallSessionResponse,
    OutboxEventSummary,
    OutboxReplayRequest,
    AnnRebuildRequest,
)

# Import helper functions from extracted module
from somabrain.api.memory.helpers import (
    _get_embedder,
    _get_wm,
    _get_memory_pool,
    _resolve_namespace,
    _serialize_coord,
    _compose_memory_payload,
    _map_retrieval_to_memory_items as _map_retrieval_items_helper,
    _coerce_to_retrieval_request as _coerce_request_helper,
)

# Import session store from extracted module
from somabrain.api.memory.session import get_recall_session_store

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
from somabrain.auth import require_auth, require_admin_auth
from somabrain.schemas import RetrievalRequest
from somabrain.tenant import get_tenant as get_tenant_async
from somabrain.db import outbox as outbox_db

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


def _store_recall_session(
    session_id: str,
    tenant: str,
    namespace: str,
    conversation_id: Optional[str],
    scoring_mode: Optional[str],
    results: List[MemoryRecallItem],
) -> None:
    """Store a recall session with results."""
    get_recall_session_store().store(
        session_id=session_id,
        tenant=tenant,
        namespace=namespace,
        conversation_id=conversation_id,
        scoring_mode=scoring_mode,
        results=results,
    )


# ============================================================================
# REMEMBER ENDPOINTS
# ============================================================================


@router.post("/remember", response_model=MemoryWriteResponse)
async def remember_memory(payload: MemoryWriteRequest, request: Request) -> MemoryWriteResponse:
    """Store a memory in both WM and LTM."""
    await _ensure_config_runtime_started()
    pool = _get_memory_pool()
    wm = _get_wm()
    embedder = _get_embedder()
    resolved_ns = _resolve_namespace(payload.tenant, payload.namespace)
    memsvc = MemoryService(pool, resolved_ns)
    memsvc._reset_circuit_if_needed()

    actor = request.headers.get("X-Actor") or "memory-api"
    stored_payload, signal_data, seed_text = _compose_memory_payload(
        tenant=payload.tenant,
        namespace=payload.namespace,
        key=payload.key,
        value=payload.value,
        meta=payload.meta,
        universe=payload.universe,
        attachments=payload.attachments,
        links=payload.links,
        tags=payload.tags,
        policy_tags=payload.policy_tags,
        signals=payload.signals,
        importance=payload.importance,
        novelty=payload.novelty,
        ttl_seconds=payload.ttl_seconds,
        trace_id=payload.trace_id,
        actor=actor,
    )

    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    persisted_to_ltm = False
    coord = None
    degraded_warnings: List[str] = []

    # Check if circuit is open - if so, queue locally and continue with WM-only
    circuit_open = memsvc._is_circuit_open()

    if circuit_open:
        # Queue to local journal for replay when backend recovers
        memsvc._queue_degraded("remember", {"key": payload.key, "payload": stored_payload})
        degraded_warnings.append("memory-backend-unavailable:queued-for-replay")
    else:
        try:
            coord = await memsvc.aremember(payload.key, stored_payload)
            persisted_to_ltm = True
        except RuntimeError as exc:
            # Circuit just opened - queue locally
            memsvc._queue_degraded("remember", {"key": payload.key, "payload": stored_payload})
            degraded_warnings.append(f"memory-backend-failed:queued-for-replay:{exc}")
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"store failed: {exc}") from exc

    coordinate_list = _serialize_coord(coord)
    if coordinate_list is not None:
        stored_payload["coordinate"] = coordinate_list

    promoted_to_wm = False
    warnings: List[str] = []
    tiered_vector: Optional[np.ndarray] = None
    try:
        vec = np.asarray(embedder.embed(seed_text), dtype=np.float32)
        wm.admit(payload.tenant, vec, stored_payload)
        promoted_to_wm = True
        tiered_vector = vec
    except Exception as exc:
        warnings.append(f"working-memory-admit-failed:{exc}")

    try:
        items = len(wm.items(payload.tenant))
    except Exception:
        items = 0
    try:
        record_memory_snapshot(payload.tenant, payload.namespace, items=items)
    except Exception:
        pass

    signal_feedback = MemorySignalFeedback(
        importance=signal_data.get("importance"),
        novelty=signal_data.get("novelty"),
        ttl_seconds=signal_data.get("ttl_seconds"),
        reinforcement=signal_data.get("reinforcement"),
        recall_bias=signal_data.get("recall_bias"),
        promoted_to_wm=promoted_to_wm,
        persisted_to_ltm=persisted_to_ltm,
    )

    anchor_id = payload.key or request_id
    if tiered_vector is not None:
        snapshot = copy.deepcopy(stored_payload)
        _TIERED_REGISTRY.remember(
            payload.tenant,
            payload.namespace,
            anchor_id=anchor_id,
            key_vector=tiered_vector,
            value_vector=tiered_vector,
            payload=snapshot,
            coordinate=coordinate_list,
        )

    # Combine degraded warnings with other warnings
    all_warnings = degraded_warnings + warnings

    return MemoryWriteResponse(
        ok=True,
        tenant=payload.tenant,
        namespace=payload.namespace,
        coordinate=coordinate_list,
        promoted_to_wm=promoted_to_wm,
        persisted_to_ltm=persisted_to_ltm,
        deduplicated=False,
        importance=signal_feedback.importance,
        novelty=signal_feedback.novelty,
        ttl_applied=signal_feedback.ttl_seconds,
        trace_id=payload.trace_id,
        request_id=request_id,
        warnings=all_warnings,
        signals=signal_feedback,
    )


@router.post("/remember/batch", response_model=MemoryBatchWriteResponse)
async def remember_memory_batch(
    payload: MemoryBatchWriteRequest, request: Request
) -> MemoryBatchWriteResponse:
    """Store multiple memories in batch."""
    await _ensure_config_runtime_started()
    pool = _get_memory_pool()
    wm = _get_wm()
    embedder = _get_embedder()
    resolved_ns = _resolve_namespace(payload.tenant, payload.namespace)
    memsvc = MemoryService(pool, resolved_ns)
    memsvc._reset_circuit_if_needed()

    actor = request.headers.get("X-Actor") or "memory-api"
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    item_contexts: List[Dict[str, Any]] = []

    for item in payload.items:
        stored_payload, signal_data, seed_text = _compose_memory_payload(
            tenant=payload.tenant,
            namespace=payload.namespace,
            key=item.key,
            value=item.value,
            meta=item.meta,
            universe=item.universe or payload.universe,
            attachments=item.attachments,
            links=item.links,
            tags=item.tags,
            policy_tags=item.policy_tags,
            signals=item.signals,
            importance=item.importance,
            novelty=item.novelty,
            ttl_seconds=item.ttl_seconds,
            trace_id=item.trace_id,
            actor=actor,
        )
        vector = None
        warnings: List[str] = []
        try:
            vector = np.asarray(embedder.embed(seed_text), dtype=np.float32)
        except Exception as exc:
            warnings.append(f"working-memory-embed-failed:{exc}")
        item_contexts.append(
            {
                "key": item.key,
                "payload": stored_payload,
                "signal_data": signal_data,
                "seed_text": seed_text,
                "trace_id": item.trace_id,
                "vector": vector,
                "warnings": warnings,
            }
        )

    if not item_contexts:
        return MemoryBatchWriteResponse(
            ok=True, tenant=payload.tenant, namespace=payload.namespace, results=[]
        )

    try:
        coords = await memsvc.aremember_bulk(
            [(ctx["key"], ctx["payload"]) for ctx in item_contexts], universe=None
        )
        persisted_to_ltm = True
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail={"message": str(exc)}) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"store failed: {exc}") from exc

    results: List[MemoryBatchWriteResult] = []
    for idx, ctx in enumerate(item_contexts):
        raw_coord = coords[idx] if idx < len(coords) else None
        coordinate = _serialize_coord(raw_coord)
        if coordinate is not None:
            try:
                ctx["payload"]["coordinate"] = coordinate
            except Exception:
                pass

        promoted_to_wm = False
        if ctx["vector"] is not None:
            try:
                wm.admit(payload.tenant, ctx["vector"], ctx["payload"])
                promoted_to_wm = True
            except Exception as exc:
                ctx["warnings"].append(f"working-memory-admit-failed:{exc}")
            snapshot = copy.deepcopy(ctx["payload"])
            _TIERED_REGISTRY.remember(
                payload.tenant,
                payload.namespace,
                anchor_id=ctx["key"],
                key_vector=ctx["vector"],
                value_vector=ctx["vector"],
                payload=snapshot,
                coordinate=coordinate,
            )

        signal_feedback = MemorySignalFeedback(
            importance=ctx["signal_data"].get("importance"),
            novelty=ctx["signal_data"].get("novelty"),
            ttl_seconds=ctx["signal_data"].get("ttl_seconds"),
            reinforcement=ctx["signal_data"].get("reinforcement"),
            recall_bias=ctx["signal_data"].get("recall_bias"),
            promoted_to_wm=promoted_to_wm,
            persisted_to_ltm=persisted_to_ltm,
        )
        results.append(
            MemoryBatchWriteResult(
                key=ctx["key"],
                coordinate=coordinate,
                promoted_to_wm=promoted_to_wm,
                persisted_to_ltm=persisted_to_ltm,
                deduplicated=False,
                importance=signal_feedback.importance,
                novelty=signal_feedback.novelty,
                ttl_applied=signal_feedback.ttl_seconds,
                trace_id=ctx["trace_id"],
                request_id=f"{request_id}:{idx}",
                warnings=ctx["warnings"],
                signals=signal_feedback,
            )
        )

    try:
        items = len(wm.items(payload.tenant))
        record_memory_snapshot(payload.tenant, payload.namespace, items=items)
    except Exception:
        pass

    return MemoryBatchWriteResponse(
        ok=True, tenant=payload.tenant, namespace=payload.namespace, results=results
    )


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
# METRICS AND ADMIN ENDPOINTS
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


@router.post("/admin/rebuild-ann")
async def rebuild_ann_indexes(payload: AnnRebuildRequest) -> Dict[str, Any]:
    """Admin: Rebuild ANN indexes."""
    await _ensure_config_runtime_started()
    results = _TIERED_REGISTRY.rebuild(payload.tenant, namespace=payload.namespace)
    return {"ok": True, "results": results}


@router.get("/admin/outbox", response_model=List[OutboxEventSummary])
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


@router.post("/admin/outbox/replay")
async def replay_outbox_events(request: Request, payload: OutboxReplayRequest) -> Dict[str, Any]:
    """Admin: Replay outbox events."""
    cfg = getattr(request.app.state, "cfg", None)
    require_admin_auth(request, cfg)
    try:
        updated = outbox_db.mark_events_for_replay(payload.ids)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Replay failed: {exc}") from exc
    return {"ok": True, "updated": int(updated)}
