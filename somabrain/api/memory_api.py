"""Memory API (No-Kong edition).

Provides FastAPI endpoints for governed memory read/write operations against the
real runtime singletons (working memory + multi-tenant memory pool). The
endpoints are thin wrappers that keep all logic inside the production services
so they stay in sync with the main application surface.
"""

from __future__ import annotations

import copy
import os
import time
import uuid
from threading import RLock
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from somabrain.metrics import (
    observe_recall_latency,
    record_memory_snapshot,
)
from somabrain.services.memory_service import MemoryService
from somabrain.services.tiered_memory_registry import TieredMemoryRegistry
from somabrain.services.parameter_supervisor import MetricsSnapshot
from somabrain.runtime.config_runtime import (
    ensure_config_dispatcher,
    ensure_supervisor_worker,
    register_config_listener,
    submit_metrics_snapshot,
    get_cutover_controller,
)
from somabrain.config import get_config
from somabrain.tenant import get_tenant
from somabrain.auth import require_auth
from somabrain.schemas import RetrievalRequest

router = APIRouter(prefix="/memory", tags=["memory"])

_RECALL_SESSIONS: Dict[str, Dict[str, Any]] = {}
_RECALL_SESSION_LOCK = RLock()
_RECALL_SESSION_TTL_SECONDS = 900

_TIERED_REGISTRY = TieredMemoryRegistry()


def _handle_config_event(event) -> None:
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
    except Exception:
        pass


register_config_listener(_handle_config_event)


async def _ensure_config_runtime_started() -> None:
    await ensure_config_dispatcher()
    await ensure_supervisor_worker()


class MemoryAttachment(BaseModel):
    kind: str = Field(..., description="Attachment type identifier")
    uri: Optional[str] = Field(None, description="External location reference")
    content_type: Optional[str] = Field(
        None, description="MIME type for the attachment"
    )
    checksum: Optional[str] = Field(
        None, description="Integrity checksum for validation"
    )
    data: Optional[str] = Field(
        None,
        description="Inline base64-encoded payload; use sparingly for small blobs",
    )
    meta: Optional[Dict[str, Any]] = Field(
        None, description="Attachment metadata annotations"
    )


class MemoryLink(BaseModel):
    rel: str = Field(..., description="Relationship descriptor (e.g. causes, follows)")
    target: str = Field(..., description="Target memory key or URI")
    weight: Optional[float] = Field(None, ge=0.0, description="Optional link strength")
    meta: Optional[Dict[str, Any]] = Field(None, description="Additional link metadata")


class MemorySignalPayload(BaseModel):
    importance: Optional[float] = Field(
        None, ge=0.0, description="Relative importance weight"
    )
    novelty: Optional[float] = Field(
        None, ge=0.0, description="Novelty score from agent"
    )
    ttl_seconds: Optional[int] = Field(
        None, ge=0, description="Soft time-to-live for cleanup"
    )
    reinforcement: Optional[str] = Field(
        None, description="Working-memory reinforcement hint (e.g. boost, suppress)"
    )
    recall_bias: Optional[str] = Field(
        None, description="Preferred recall strategy (explore, exploit, balanced, etc.)"
    )


class MemorySignalFeedback(BaseModel):
    importance: Optional[float] = None
    novelty: Optional[float] = None
    ttl_seconds: Optional[int] = Field(None, ge=0, description="Applied ttl in seconds")
    reinforcement: Optional[str] = None
    recall_bias: Optional[str] = None
    promoted_to_wm: Optional[bool] = None
    persisted_to_ltm: Optional[bool] = None


class MemoryWriteRequest(BaseModel):
    tenant: str = Field(..., min_length=1, description="Tenant identifier")
    namespace: str = Field(
        ..., min_length=1, description="Logical namespace (e.g. wm, ltm)"
    )
    key: str = Field(
        ..., min_length=1, description="Stable key used to derive coordinates"
    )
    value: Dict[str, Any] = Field(..., description="Payload stored in memory")
    meta: Optional[Dict[str, Any]] = Field(
        None, description="Optional metadata blended into the stored payload"
    )
    universe: Optional[str] = Field(
        None, description="Universe scope forwarded to the memory backend"
    )
    ttl_seconds: Optional[int] = Field(
        None, ge=0, description="Desired time-to-live hint for automatic cleanup"
    )
    tags: List[str] = Field(
        default_factory=list, description="Arbitrary agent-supplied tags"
    )
    policy_tags: List[str] = Field(
        default_factory=list, description="Policy or governance tags for this memory"
    )
    attachments: List[MemoryAttachment] = Field(
        default_factory=list, description="Optional attachment descriptors"
    )
    links: List[MemoryLink] = Field(
        default_factory=list, description="Optional outbound links to existing memories"
    )
    signals: Optional[MemorySignalPayload] = Field(
        None, description="Agent-provided signals guiding storage priorities"
    )
    importance: Optional[float] = Field(
        None, ge=0.0, description="Shortcut for signals.importance"
    )
    novelty: Optional[float] = Field(
        None, ge=0.0, description="Shortcut for signals.novelty"
    )
    trace_id: Optional[str] = Field(
        None, description="Agent correlation identifier for downstream observability"
    )


class MemoryWriteResponse(BaseModel):
    ok: bool
    tenant: str
    namespace: str
    coordinate: Optional[List[float]] = None
    promoted_to_wm: bool = False
    persisted_to_ltm: bool = False
    deduplicated: bool = False
    importance: Optional[float] = None
    novelty: Optional[float] = None
    ttl_applied: Optional[int] = None
    trace_id: Optional[str] = None
    request_id: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    signals: Optional[MemorySignalFeedback] = None


class MemoryRecallRequest(BaseModel):
    tenant: str = Field(..., min_length=1)
    namespace: str = Field(..., min_length=1)
    query: str = Field(..., min_length=1)
    top_k: int = Field(3, ge=1, le=50)
    layer: Optional[str] = Field(
        None, description="Set to 'wm', 'ltm', or omit for both"
    )
    universe: Optional[str] = None
    tags: List[str] = Field(
        default_factory=list, description="Filter hits containing these tags"
    )
    min_score: Optional[float] = Field(
        None, ge=0.0, description="Drop hits with score below this threshold"
    )
    max_age_seconds: Optional[int] = Field(
        None,
        ge=0,
        description="Exclude hits older than the specified age when payload timestamps exist",
    )
    scoring_mode: Optional[str] = Field(
        None,
        description="Preferred scoring strategy (explore, exploit, blended, recency, etc.)",
    )
    session_id: Optional[str] = Field(
        None, description="Attach to existing recall session to accumulate context"
    )
    conversation_id: Optional[str] = Field(
        None, description="Agent-provided conversation identifier"
    )
    pin_results: bool = Field(
        False,
        description="If true, persist results in the session registry for follow-up queries",
    )
    chunk_size: Optional[int] = Field(
        None,
        ge=1,
        le=50,
        description="Limit number of hits returned per call for streaming",
    )
    chunk_index: int = Field(
        0,
        ge=0,
        description="Chunk index when requesting paged/streamed recall segments",
    )


class MemoryRecallItem(BaseModel):
    layer: str
    score: Optional[float] = None
    payload: Dict[str, Any]
    coordinate: Optional[List[float]] = None
    source: str
    confidence: Optional[float] = Field(
        None, description="Confidence score derived from backend metrics"
    )
    novelty: Optional[float] = Field(
        None, description="Novelty indicator relative to session history"
    )
    affinity: Optional[float] = Field(
        None, description="Affinity to current conversation or goal state"
    )


class MemoryRecallResponse(BaseModel):
    tenant: str
    namespace: str
    results: List[MemoryRecallItem]
    wm_hits: int
    ltm_hits: int
    duration_ms: float
    session_id: str
    scoring_mode: Optional[str] = None
    chunk_index: int = 0
    has_more: bool = False
    total_results: int
    chunk_size: Optional[int] = None
    conversation_id: Optional[str] = None


class CutoverOpenRequest(BaseModel):
    tenant: str = Field(..., min_length=1)
    from_namespace: str = Field(..., min_length=1)
    to_namespace: str = Field(..., min_length=1)


class CutoverActionRequest(BaseModel):
    tenant: str = Field(..., min_length=1)
    reason: Optional[str] = None


class CutoverPlanResponse(BaseModel):
    tenant: str
    from_namespace: str
    to_namespace: str
    status: str
    ready: bool
    created_at: float
    approved_at: Optional[float] = None
    notes: List[str] = Field(default_factory=list)
    last_top1_accuracy: Optional[float] = None
    last_margin: Optional[float] = None
    last_latency_p95_ms: Optional[float] = None
def _tiered_enabled() -> bool:
    flag = os.getenv("ENABLE_TIERED_MEMORY", "0").strip().lower()
    return flag in ("1", "true", "yes", "on")



class MemoryMetricsResponse(BaseModel):
    tenant: str
    namespace: str
    wm_items: int
    circuit_open: bool


class MemoryBatchWriteItem(BaseModel):
    key: str = Field(..., min_length=1)
    value: Dict[str, Any] = Field(..., description="Payload stored in memory")
    meta: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")
    ttl_seconds: Optional[int] = Field(
        None, ge=0, description="TTL override for this item"
    )
    tags: List[str] = Field(default_factory=list, description="Optional tags")
    policy_tags: List[str] = Field(default_factory=list, description="Policy tags")
    attachments: List[MemoryAttachment] = Field(default_factory=list)
    links: List[MemoryLink] = Field(default_factory=list)
    signals: Optional[MemorySignalPayload] = None
    importance: Optional[float] = Field(None, ge=0.0)
    novelty: Optional[float] = Field(None, ge=0.0)
    trace_id: Optional[str] = None
    universe: Optional[str] = None


class MemoryBatchWriteRequest(BaseModel):
    tenant: str = Field(..., min_length=1)
    namespace: str = Field(..., min_length=1)
    items: List[MemoryBatchWriteItem] = Field(
        ..., min_items=1, description="Batch of memories to persist"
    )
    universe: Optional[str] = Field(
        None,
        description="Default universe applied when items omit universe; item value wins",
    )


class MemoryBatchWriteResult(BaseModel):
    key: str
    coordinate: Optional[List[float]] = None
    promoted_to_wm: bool = False
    persisted_to_ltm: bool = False
    deduplicated: bool = False
    importance: Optional[float] = None
    novelty: Optional[float] = None
    ttl_applied: Optional[int] = None
    trace_id: Optional[str] = None
    request_id: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    signals: Optional[MemorySignalFeedback] = None


class MemoryBatchWriteResponse(BaseModel):
    ok: bool
    tenant: str
    namespace: str
    results: List[MemoryBatchWriteResult]
    


class MemoryRecallSessionResponse(BaseModel):
    session_id: str
    tenant: str
    namespace: str
    scoring_mode: Optional[str]
    conversation_id: Optional[str]
    created_at: float
    results: List[MemoryRecallItem]


def _runtime_module():
    from somabrain import runtime as rt

    return rt


def _app_config():
    rt = _runtime_module()
    cfg = getattr(rt, "cfg", None)
    if cfg is None:
        from somabrain.config import get_config

        cfg = get_config()
        setattr(rt, "cfg", cfg)
    return cfg


def _resolve_namespace(tenant: str, namespace: str) -> str:
    base = getattr(_app_config(), "namespace", "somabrain")
    tenant_part = tenant.strip() or "public"
    ns_part = namespace.strip()
    core = f"{base}:{tenant_part}"
    return f"{core}:{ns_part}" if ns_part else core


def _get_embedder():
    embedder = getattr(_runtime_module(), "embedder", None)
    if embedder is None:
        raise HTTPException(status_code=503, detail="embedder unavailable")
    return embedder


def _get_wm():
    wm = getattr(_runtime_module(), "mt_wm", None)
    if wm is None:
        raise HTTPException(status_code=503, detail="working memory unavailable")
    return wm


def _get_memory_pool():
    pool = getattr(_runtime_module(), "mt_memory", None)
    if pool is None:
        raise HTTPException(status_code=503, detail="memory pool unavailable")
    return pool


def _serialize_coord(coord: Any) -> Optional[List[float]]:
    if isinstance(coord, (list, tuple)) and len(coord) == 3:
        try:
            return [float(coord[0]), float(coord[1]), float(coord[2])]
        except Exception:
            return None
    return None


# Removed: no local outbox support


def _prune_sessions() -> None:
    now = time.time()
    with _RECALL_SESSION_LOCK:
        expired = [
            session_id
            for session_id, state in _RECALL_SESSIONS.items()
            if now - state.get("created_at", 0.0) > _RECALL_SESSION_TTL_SECONDS
        ]
        for session_id in expired:
            _RECALL_SESSIONS.pop(session_id, None)


def _compose_memory_payload(
    *,
    tenant: str,
    namespace: str,
    key: str,
    value: Dict[str, Any],
    meta: Optional[Dict[str, Any]],
    universe: Optional[str],
    attachments: List[MemoryAttachment],
    links: List[MemoryLink],
    tags: List[str],
    policy_tags: List[str],
    signals: Optional[MemorySignalPayload],
    importance: Optional[float],
    novelty: Optional[float],
    ttl_seconds: Optional[int],
    trace_id: Optional[str],
    actor: str,
) -> tuple[Dict[str, Any], Dict[str, Any], str]:
    stored_payload: Dict[str, Any] = dict(value)
    stored_payload.setdefault("task", stored_payload.get("text") or key)
    stored_payload.setdefault("tenant_id", tenant)
    stored_payload.setdefault("namespace", namespace)
    stored_payload.setdefault("tenant", tenant)
    stored_payload.setdefault("key", key)
    stored_payload.setdefault(
        "memory_type", stored_payload.get("memory_type", "episodic")
    )
    if meta:
        incoming_meta = dict(meta)
        existing_meta = stored_payload.get("meta")
        if isinstance(existing_meta, dict):
            merged_meta = dict(existing_meta)
            merged_meta.update(incoming_meta)
            stored_payload["meta"] = merged_meta
        else:
            stored_payload["meta"] = incoming_meta
    stored_payload["tags"] = list(dict.fromkeys(tags or []))
    stored_payload["policy_tags"] = list(dict.fromkeys(policy_tags or []))
    if attachments:
        stored_payload["attachments"] = [
            attachment.dict(exclude_none=True) for attachment in attachments
        ]
    if links:
        stored_payload["links"] = [link.dict(exclude_none=True) for link in links]
    if universe:
        stored_payload["universe"] = universe
    else:
        stored_payload.setdefault("universe", "real")
    stored_payload.setdefault("_actor", actor)
    if trace_id:
        stored_payload["trace_id"] = trace_id

    signal_data: Dict[str, Any] = {}
    if signals is not None:
        signal_data.update(signals.dict(exclude_none=True))
    if importance is not None:
        signal_data["importance"] = importance
    if novelty is not None:
        signal_data["novelty"] = novelty
    if ttl_seconds is not None:
        stored_payload["ttl_seconds"] = ttl_seconds
        signal_data.setdefault("ttl_seconds", ttl_seconds)
    if signal_data:
        stored_payload["signals"] = signal_data

    seed_text = (
        stored_payload.get("task")
        or stored_payload.get("text")
        or stored_payload.get("content")
        or key
    )

    return stored_payload, signal_data, str(seed_text)


def _store_recall_session(
    session_id: str,
    tenant: str,
    namespace: str,
    conversation_id: Optional[str],
    scoring_mode: Optional[str],
    results: List[MemoryRecallItem],
) -> None:
    payload = {
        "session_id": session_id,
        "tenant": tenant,
        "namespace": namespace,
        "conversation_id": conversation_id,
        "scoring_mode": scoring_mode,
        "created_at": time.time(),
        "results": [item.dict() for item in results],
    }
    with _RECALL_SESSION_LOCK:
        _RECALL_SESSIONS[session_id] = payload


@router.post("/remember", response_model=MemoryWriteResponse)
async def remember_memory(
    payload: MemoryWriteRequest, request: Request
) -> MemoryWriteResponse:
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
    breaker_state = memsvc._is_circuit_open()

    try:
        coord = await memsvc.aremember(payload.key, stored_payload)
        persisted_to_ltm = True
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail={"message": str(exc)}) from exc
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
        warnings=warnings,
        signals=signal_feedback,
    )


@router.post("/remember/batch", response_model=MemoryBatchWriteResponse)
async def remember_memory_batch(
    payload: MemoryBatchWriteRequest, request: Request
) -> MemoryBatchWriteResponse:
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
            ok=True,
            tenant=payload.tenant,
            namespace=payload.namespace,
            results=[],
        )

    try:
        coords = await memsvc.aremember_bulk(
            [(ctx["key"], ctx["payload"]) for ctx in item_contexts],
            universe=None,
        )
        persisted_to_ltm = True
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail={"message": str(exc)}) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"store failed: {exc}") from exc

    results: List[MemoryBatchWriteResult] = []
    persisted_to_ltm = True
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

        if ctx["vector"] is not None:
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
    except Exception:
        items = 0
    try:
        record_memory_snapshot(payload.tenant, payload.namespace, items=items)
    except Exception:
        pass

    return MemoryBatchWriteResponse(
        ok=True,
        tenant=payload.tenant,
        namespace=payload.namespace,
        results=results,
    )


async def _perform_recall(
    payload: MemoryRecallRequest, *, default_chunk_size: Optional[int] = None
) -> MemoryRecallResponse:
    await _ensure_config_runtime_started()
    layer = (payload.layer or "all").lower()
    if layer not in {"wm", "ltm", "all"}:
        raise HTTPException(status_code=400, detail="layer must be wm, ltm, or omitted")

    chunk_size = payload.chunk_size or default_chunk_size
    chunk_index = payload.chunk_index if payload.chunk_index >= 0 else 0

    wm_hits: List[MemoryRecallItem] = []
    ltm_hits: List[MemoryRecallItem] = []
    start = time.perf_counter()

    embedder = None
    query_vec: Optional[np.ndarray] = None
    try:
        embedder = _get_embedder()
        query_vec = np.asarray(embedder.embed(payload.query), dtype=np.float32)
    except HTTPException:
        if layer in {"wm", "all"}:
            raise
    except Exception:
        embedder = None
        query_vec = None

    def _match_tags(candidate: Dict[str, Any]) -> bool:
        if not payload.tags:
            return True
        candidate_tags = set()
        for key in ("tags", "labels"):
            value = candidate.get(key)
            if isinstance(value, (list, tuple, set)):
                candidate_tags.update(str(v) for v in value)
        meta = candidate.get("meta")
        if isinstance(meta, dict):
            meta_tags = meta.get("tags")
            if isinstance(meta_tags, (list, tuple, set)):
                candidate_tags.update(str(v) for v in meta_tags)
        return all(tag in candidate_tags for tag in payload.tags)

    def _within_age(candidate: Dict[str, Any]) -> bool:
        if payload.max_age_seconds is None:
            return True
        ts_keys = ("ts", "timestamp", "created_at", "time", "datetime")
        for key in ts_keys:
            value = candidate.get(key)
            if value is None and isinstance(candidate.get("meta"), dict):
                value = candidate["meta"].get(key)
            if value is None:
                continue
            try:
                if isinstance(value, (int, float)):
                    ts = float(value)
                elif isinstance(value, str):
                    ts = float(value)
                else:
                    continue
                return time.time() - ts <= payload.max_age_seconds
            except Exception:
                continue
        return False

    def _decorated_item(
        layer_name: str,
        source: str,
        score_val: Optional[float],
        candidate_payload: Dict[str, Any],
        coord_obj: Any,
    ) -> Optional[MemoryRecallItem]:
        if not _match_tags(candidate_payload):
            return None
        if not _within_age(candidate_payload):
            return None
        if payload.min_score is not None and score_val is not None:
            if score_val < payload.min_score:
                return None
        signals = candidate_payload.get("signals")
        importance = None
        novelty = None
        affinity = None
        if isinstance(signals, dict):
            importance = signals.get("importance")
            novelty = signals.get("novelty")
            affinity = signals.get("recall_bias") or signals.get("reinforcement")
        if importance is None:
            importance = candidate_payload.get("importance")
        if novelty is None:
            novelty = candidate_payload.get("novelty")
        if affinity is None:
            affinity = candidate_payload.get("affinity")
        confidence = float(score_val) if score_val is not None else importance
        return MemoryRecallItem(
            layer=layer_name,
            score=float(score_val) if score_val is not None else None,
            payload=candidate_payload,
            coordinate=_serialize_coord(coord_obj),
            source=source,
            confidence=confidence,
            novelty=novelty,
            affinity=affinity if affinity is not None else importance,
        )

    if layer in {"wm", "all"} and query_vec is not None:
        try:
            wm = _get_wm()
            stage_start = time.perf_counter()
            hits = wm.recall(payload.tenant, query_vec, top_k=payload.top_k)
            stage_dur = time.perf_counter() - stage_start
            try:
                from somabrain import metrics as M

                M.RECALL_WM_LAT.labels(cohort="memory_api").observe(stage_dur)
            except Exception:
                pass
            for score, item_payload in hits:
                if not isinstance(item_payload, dict):
                    continue
                item = _decorated_item(
                    "wm",
                    "working_memory",
                    float(score) if score is not None else None,
                    item_payload,
                    item_payload.get("coordinate"),
                )
                if item is not None:
                    wm_hits.append(item)
        except HTTPException:
            raise
        except Exception:
            pass

    if layer in {"ltm", "all"}:
        pool = _get_memory_pool()
        resolved_ns = _resolve_namespace(payload.tenant, payload.namespace)
        memsvc = MemoryService(pool, resolved_ns)
        memsvc._reset_circuit_if_needed()
        client = memsvc.client()
        stage_start = time.perf_counter()
        try:
            hits = await client.arecall(
                payload.query,
                top_k=payload.top_k,
                universe=payload.universe or "real",
            )
        except RuntimeError as exc:
            raise HTTPException(status_code=503, detail={"message": str(exc)}) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=502, detail=f"recall failed: {exc}"
            ) from exc
        stage_dur = time.perf_counter() - stage_start
        try:
            from somabrain import metrics as M

            M.RECALL_LTM_LAT.labels(cohort="memory_api").observe(stage_dur)
        except Exception:
            pass
        for hit in hits:
            payload_obj = getattr(hit, "payload", None)
            if not isinstance(payload_obj, dict):
                continue
            coord = getattr(hit, "coordinate", None) or payload_obj.get("coordinate")
            score_val = getattr(hit, "score", None)
            item = _decorated_item(
                "ltm",
                "long_term_memory",
                float(score_val) if score_val is not None else None,
                payload_obj,
                coord,
            )
            if item is not None:
                ltm_hits.append(item)

    tiered_item: Optional[MemoryRecallItem] = None
    tiered_margin_value: Optional[float] = None
    tiered_eta_value: Optional[float] = None
    tiered_sparsity_value: Optional[float] = None
    if _tiered_enabled() and query_vec is not None:
        try:
            tiered_hit = _TIERED_REGISTRY.recall(
                payload.tenant,
                payload.namespace,
                query_vector=query_vec,
            )
        except Exception:
            tiered_hit = None
        if tiered_hit is not None and tiered_hit.payload is not None:
            payload_copy = copy.deepcopy(tiered_hit.payload)
            payload_copy.setdefault("governed_margin", tiered_hit.context.margin)
            payload_copy.setdefault("cleanup_backend", tiered_hit.backend)
            coord_obj = tiered_hit.coordinate or payload_copy.get("coordinate")
            item = _decorated_item(
                tiered_hit.context.layer,
                "tiered_memory",
                tiered_hit.context.score,
                payload_copy,
                coord_obj,
            )
            if item is not None:
                tiered_item = item
                tiered_margin_value = tiered_hit.context.margin
                tiered_eta_value = tiered_hit.eta
                tiered_sparsity_value = tiered_hit.sparsity

    all_results: List[MemoryRecallItem] = []
    seen: set[Tuple[Optional[Tuple[float, ...]], str, str]] = set()

    def _append(item: Optional[MemoryRecallItem]) -> None:
        if item is None:
            return
        coord_key: Optional[Tuple[float, ...]]
        if item.coordinate is not None:
            coord_key = tuple(item.coordinate)
        else:
            coord_key = None
        key = (coord_key, item.layer, item.source or "")
        if key in seen:
            return
        seen.add(key)
        all_results.append(item)

    _append(tiered_item)
    for entry in wm_hits:
        _append(entry)
    for entry in ltm_hits:
        _append(entry)

    total_results = len(all_results)
    if chunk_size is not None and chunk_size > 0:
        start_index = chunk_index * chunk_size
        end_index = start_index + chunk_size
        chunk_results = all_results[start_index:end_index]
        has_more = end_index < total_results
    else:
        chunk_results = all_results
        has_more = False

    duration = time.perf_counter() - start
    try:
        observe_recall_latency(payload.namespace, duration)
    except Exception:
        pass

    current_session = payload.session_id or str(uuid.uuid4())
    _prune_sessions()
    if payload.pin_results or chunk_size is not None or payload.session_id:
        _store_recall_session(
            current_session,
            payload.tenant,
            payload.namespace,
            payload.conversation_id,
            payload.scoring_mode,
            all_results,
        )
    if tiered_margin_value is not None:
        try:
            record_memory_snapshot(
                payload.tenant,
                payload.namespace,
                margin=tiered_margin_value,
                eta=tiered_eta_value,
                sparsity=tiered_sparsity_value,
            )
        except Exception:
            pass

    top_confidence = 0.0
    if all_results:
        confidence = all_results[0].confidence
        if confidence is not None:
            try:
                top_confidence = float(confidence)
            except Exception:
                top_confidence = 0.0

    try:
        await submit_metrics_snapshot(
            MetricsSnapshot(
                tenant=payload.tenant,
                namespace=payload.namespace,
                top1_accuracy=top_confidence,
                margin=float(tiered_margin_value or 0.0),
                latency_p95_ms=duration * 1000.0,
            )
        )
    except Exception:
        pass

    # Optionally feed shadow metrics into any open cutover plan for this tenant/namespace.
    try:
        controller = get_cutover_controller()
        await controller.record_shadow_metrics(
            payload.tenant,
            payload.namespace,
            top1_accuracy=top_confidence,
            margin=float(tiered_margin_value or 0.0),
            latency_p95_ms=duration * 1000.0,
        )
    except Exception:
        # Best-effort: ignore when no plan is open or namespaces do not match.
        pass

    return MemoryRecallResponse(
        tenant=payload.tenant,
        namespace=payload.namespace,
        results=chunk_results,
        wm_hits=len(wm_hits),
        ltm_hits=len(ltm_hits),
        duration_ms=round(duration * 1000.0, 3),
        session_id=current_session,
        scoring_mode=payload.scoring_mode,
        chunk_index=chunk_index,
        has_more=has_more,
        total_results=total_results,
        chunk_size=chunk_size,
        conversation_id=payload.conversation_id,
    )


def _as_float_list(coord: object) -> Optional[List[float]]:
    if isinstance(coord, (list, tuple)) and len(coord) >= 3:
        try:
            return [float(coord[0]), float(coord[1]), float(coord[2])]
        except Exception:
            return None
    if isinstance(coord, str):
        try:
            parts = [float(x.strip()) for x in coord.split(",")]
            if len(parts) >= 3:
                return [parts[0], parts[1], parts[2]]
        except Exception:
            return None
    return None


def _map_retrieval_to_memory_items(candidates: List[dict]) -> List["MemoryRecallItem"]:
    items: List[MemoryRecallItem] = []
    for c in candidates:
        # candidate dict shape mirrors RetrievalCandidate model
        retr = str(c.get("retriever") or "vector")
        layer = "wm" if retr == "wm" else "ltm"
        payload = c.get("payload") if isinstance(c.get("payload"), dict) else {}
        score = c.get("score")
        coord = _as_float_list(c.get("coord") or payload.get("coordinate"))
        items.append(
            MemoryRecallItem(
                layer=layer,
                score=float(score) if isinstance(score, (int, float)) else None,
                payload=payload,
                coordinate=coord,
                source=retr,
                confidence=float(score) if isinstance(score, (int, float)) else None,
            )
        )
    return items


def _coerce_to_retrieval_request(obj: object, default_top_k: int = 10) -> RetrievalRequest:
    # Resolve environment-backed defaults for full-power behavior with safe rollback
    def _env(name: str, default: str | None = None) -> str | None:
        try:
            v = os.getenv(name)
            return v if v is not None and v != "" else default
        except Exception:
            return default

    def _env_bool(name: str, default: bool) -> bool:
        v = _env(name)
        if v is None:
            return default
        s = v.strip().lower()
        return s in ("1", "true", "yes", "on")

    # Master switch: full power on by default; set 0/false to revert to conservative
    full_power = _env_bool("SOMABRAIN_RECALL_FULL_POWER", True)
    simple_defaults = _env_bool("SOMABRAIN_RECALL_SIMPLE_DEFAULTS", False)

    # Compute effective defaults
    if simple_defaults or not full_power:
        eff_rerank = _env("SOMABRAIN_RECALL_DEFAULT_RERANK", "cosine")
        eff_persist = _env_bool("SOMABRAIN_RECALL_DEFAULT_PERSIST", False)
        eff_retrievers = (
            (_env("SOMABRAIN_RECALL_DEFAULT_RETRIEVERS", "vector,wm,graph") or "")
            .split(",")
        )
    else:
        eff_rerank = _env("SOMABRAIN_RECALL_DEFAULT_RERANK", "auto")
        eff_persist = _env_bool("SOMABRAIN_RECALL_DEFAULT_PERSIST", True)
        eff_retrievers = (
            (_env("SOMABRAIN_RECALL_DEFAULT_RETRIEVERS", "vector,wm,graph,lexical") or "")
            .split(",")
        )
    eff_retrievers = [r.strip() for r in eff_retrievers if r and r.strip()]

    # Accept string or dict-like (including MemoryRecallRequest dict)
    if isinstance(obj, str):
        req = RetrievalRequest(query=obj, top_k=default_top_k)
        # Apply env-backed defaults when caller did not specify
        req.rerank = eff_rerank or req.rerank
        req.persist = eff_persist if req.persist is None or isinstance(req.persist, bool) else req.persist
        if not req.retrievers:
            req.retrievers = eff_retrievers or req.retrievers
        return req
    if isinstance(obj, MemoryRecallRequest):
        req = RetrievalRequest(
            query=obj.query,
            top_k=int(obj.top_k or default_top_k),
            universe=obj.universe,
        )
        # Apply env-backed defaults when not provided by caller
        req.rerank = eff_rerank or req.rerank
        req.persist = eff_persist if req.persist is None or isinstance(req.persist, bool) else req.persist
        if not req.retrievers:
            req.retrievers = eff_retrievers or req.retrievers
        return req
    if isinstance(obj, dict):
        d = dict(obj)
        q = d.get("query") or d.get("q") or ""
        rk = d.get("rerank")
        retr = d.get("retrievers")
        # Advanced hints
        mode = d.get("mode")
        idv = d.get("id")
        keyv = d.get("key")
        coord = d.get("coord")
        uni = d.get("universe")
        tk = int(d.get("top_k") or default_top_k)
        req = RetrievalRequest(
            query=str(q),
            top_k=tk,
            retrievers=list(retr) if isinstance(retr, list) else RetrievalRequest().retrievers,
            rerank=str(rk) if isinstance(rk, str) else RetrievalRequest().rerank,
            persist=bool(d.get("persist")) if d.get("persist") is not None else RetrievalRequest().persist,
            universe=str(uni) if isinstance(uni, str) else None,
            mode=str(mode) if isinstance(mode, str) else None,
            id=str(idv) if isinstance(idv, str) else None,
            key=str(keyv) if isinstance(keyv, str) else None,
            coord=str(coord) if isinstance(coord, str) else None,
        )
        # If caller omitted fields, enforce env-backed defaults
        if not isinstance(retr, list) or not retr:
            req.retrievers = eff_retrievers or req.retrievers
        if not isinstance(rk, str) or not rk:
            req.rerank = eff_rerank or req.rerank
        if d.get("persist") is None:
            req.persist = eff_persist
        return req
    # Fallback: stringify unknown payload
    req = RetrievalRequest(query=str(obj), top_k=default_top_k)
    req.rerank = eff_rerank or req.rerank
    req.persist = eff_persist if req.persist is None or isinstance(req.persist, bool) else req.persist
    if not req.retrievers:
        req.retrievers = eff_retrievers or req.retrievers
    return req


@router.post("/recall", response_model=MemoryRecallResponse)
async def recall_memory(payload: object, request: Request) -> MemoryRecallResponse:
    """Unified recall endpoint backed by the retrieval pipeline.

    Accepts either a plain string (JSON string) or an object body. For object bodies,
    accepts the legacy MemoryRecallRequest fields as well as RetrievalRequest fields.
    """
    await _ensure_config_runtime_started()
    cfg = get_config()
    ctx = get_tenant(request, cfg.namespace)
    require_auth(request, cfg)

    # Coerce incoming payload to a RetrievalRequest
    ret_req = _coerce_to_retrieval_request(payload, default_top_k=10)

    # Run pipeline
    import time as _time
    t0 = _time.perf_counter()
    from somabrain.services.retrieval_pipeline import run_retrieval_pipeline

    ret_resp = await run_retrieval_pipeline(ret_req, ctx=ctx, cfg=cfg, universe=ret_req.universe, trace_id=request.headers.get("X-Request-ID"))
    dt_ms = round(( _time.perf_counter() - t0) * 1000.0, 3)

    # Map candidates to MemoryRecallItems
    # Convert RetrievalResponse (pydantic) to dict for portability
    ret_dict = ret_resp.dict() if hasattr(ret_resp, "dict") else ret_resp  # type: ignore
    cands = ret_dict.get("candidates") or []
    items = _map_retrieval_to_memory_items(cands)

    # Counts by retriever
    wm_hits = sum(1 for it in items if it.layer == "wm")
    ltm_hits = sum(1 for it in items if it.layer != "wm")

    # Metric: count recall requests (retrieval-backed)
    try:
        from somabrain import metrics as M
        M.RECALL_REQUESTS.labels(namespace=ctx.namespace).inc()
    except Exception:
        pass

    # Prepare response
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
    )


@router.post("/recall/stream", response_model=MemoryRecallResponse)
async def recall_memory_stream(payload: object, request: Request) -> MemoryRecallResponse:
    # Provide a reasonable default chunking and reuse the unified recall.
    # We honor top_k from input if present; otherwise default to 10 and stream 5 per page.
    ret_req = _coerce_to_retrieval_request(payload, default_top_k=10)
    chunk_size = min(max(1, int(ret_req.top_k)), 5)
    # Call the unified recall first
    base = await recall_memory(payload, request)
    # Apply chunking on top of the full results for streaming semantics
    start_index = 0
    end_index = min(len(base.results), chunk_size)
    base.results = base.results[start_index:end_index]
    base.has_more = end_index < base.total_results
    base.chunk_index = 0
    base.chunk_size = chunk_size
    return base


@router.get("/context/{session_id}", response_model=MemoryRecallSessionResponse)
async def get_recall_session(session_id: str) -> MemoryRecallSessionResponse:
    _prune_sessions()
    with _RECALL_SESSION_LOCK:
        state = _RECALL_SESSIONS.get(session_id)
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


@router.get("/metrics", response_model=MemoryMetricsResponse)
async def memory_metrics(
    tenant: str = Query(..., min_length=1),
    namespace: str = Query(..., min_length=1),
) -> MemoryMetricsResponse:
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

    # No local outbox/journal; fail-fast semantics only
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
    await _ensure_config_runtime_started()
    results = _TIERED_REGISTRY.rebuild(payload.tenant, namespace=payload.namespace)
    return {"ok": True, "results": results}


class AnnRebuildRequest(BaseModel):
    tenant: str
    namespace: Optional[str] = None


def _plan_to_response(plan) -> CutoverPlanResponse:
    last = plan.last_shadow_metrics
    return CutoverPlanResponse(
        tenant=plan.tenant,
        from_namespace=plan.from_namespace,
        to_namespace=plan.to_namespace,
        status=plan.status,
        ready=plan.ready,
        created_at=plan.created_at,
        approved_at=plan.approved_at,
        notes=list(plan.notes or []),
        last_top1_accuracy=(last.top1_accuracy if last else None),
        last_margin=(last.margin if last else None),
        last_latency_p95_ms=(last.latency_p95_ms if last else None),
    )


@router.post("/cutover/open", response_model=CutoverPlanResponse)
async def cutover_open(payload: CutoverOpenRequest) -> CutoverPlanResponse:
    await _ensure_config_runtime_started()
    controller = get_cutover_controller()
    plan = await controller.open_plan(
        payload.tenant, payload.from_namespace, payload.to_namespace
    )
    return _plan_to_response(plan)


@router.post("/cutover/approve", response_model=CutoverPlanResponse)
async def cutover_approve(payload: CutoverActionRequest) -> CutoverPlanResponse:
    await _ensure_config_runtime_started()
    controller = get_cutover_controller()
    plan = await controller.approve(payload.tenant)
    return _plan_to_response(plan)


@router.post("/cutover/execute", response_model=CutoverPlanResponse)
async def cutover_execute(payload: CutoverActionRequest) -> CutoverPlanResponse:
    await _ensure_config_runtime_started()
    controller = get_cutover_controller()
    plan = await controller.execute(payload.tenant)
    return _plan_to_response(plan)


@router.post("/cutover/cancel")
async def cutover_cancel(payload: CutoverActionRequest) -> Dict[str, Any]:
    await _ensure_config_runtime_started()
    controller = get_cutover_controller()
    await controller.cancel(payload.tenant, reason=payload.reason or "")
    return {"ok": True}


@router.get("/cutover/status/{tenant}", response_model=CutoverPlanResponse)
async def cutover_status(tenant: str) -> CutoverPlanResponse:
    await _ensure_config_runtime_started()
    controller = get_cutover_controller()
    plan = controller.get_plan(tenant)
    if plan is None:
        raise HTTPException(status_code=404, detail="no active plan for tenant")
    return _plan_to_response(plan)
