"""Memory API (No-Kong edition).

Provides FastAPI endpoints for governed memory read/write operations against the
real runtime singletons (working memory + multi-tenant memory pool). The
endpoints are thin wrappers that keep all logic inside the production services
so they stay in sync with the main application surface.
"""

from __future__ import annotations

import os
import time
import uuid
from typing import Any, Dict, List, Optional

import numpy as np
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from somabrain.metrics import (
    observe_recall_latency,
    record_memory_snapshot,
)
from somabrain.services.memory_service import MemoryService

router = APIRouter(prefix="/memory", tags=["memory"])


class MemoryAttachment(BaseModel):
    kind: str = Field(..., description="Attachment type identifier")
    uri: Optional[str] = Field(None, description="External location reference")
    content_type: Optional[str] = Field(None, description="MIME type for the attachment")
    checksum: Optional[str] = Field(None, description="Integrity checksum for validation")
    data: Optional[str] = Field(
        None,
        description="Inline base64-encoded payload; use sparingly for small blobs",
    )
    meta: Optional[Dict[str, Any]] = Field(None, description="Attachment metadata annotations")


class MemoryLink(BaseModel):
    rel: str = Field(..., description="Relationship descriptor (e.g. causes, follows)")
    target: str = Field(..., description="Target memory key or URI")
    weight: Optional[float] = Field(None, ge=0.0, description="Optional link strength")
    meta: Optional[Dict[str, Any]] = Field(None, description="Additional link metadata")


class MemorySignalPayload(BaseModel):
    importance: Optional[float] = Field(None, ge=0.0, description="Relative importance weight")
    novelty: Optional[float] = Field(None, ge=0.0, description="Novelty score from agent")
    ttl_seconds: Optional[int] = Field(None, ge=0, description="Soft time-to-live for cleanup")
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
    namespace: str = Field(..., min_length=1, description="Logical namespace (e.g. wm, ltm)")
    key: str = Field(..., min_length=1, description="Stable key used to derive coordinates")
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
    tags: List[str] = Field(default_factory=list, description="Arbitrary agent-supplied tags")
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
    importance: Optional[float] = Field(None, ge=0.0, description="Shortcut for signals.importance")
    novelty: Optional[float] = Field(None, ge=0.0, description="Shortcut for signals.novelty")
    trace_id: Optional[str] = Field(
        None, description="Agent correlation identifier for downstream observability"
    )


class MemoryWriteResponse(BaseModel):
    ok: bool
    tenant: str
    namespace: str
    coordinate: Optional[List[float]] = None
    queued: bool = False
    breaker_open: bool = False
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
    top_k: int = Field(3, ge=1, le=20)
    layer: Optional[str] = Field(
        None, description="Set to 'wm', 'ltm', or omit for both"
    )
    universe: Optional[str] = None


class MemoryRecallItem(BaseModel):
    layer: str
    score: Optional[float] = None
    payload: Dict[str, Any]
    coordinate: Optional[List[float]] = None
    source: str


class MemoryRecallResponse(BaseModel):
    tenant: str
    namespace: str
    results: List[MemoryRecallItem]
    wm_hits: int
    ltm_hits: int
    duration_ms: float


class MemoryMetricsResponse(BaseModel):
    tenant: str
    namespace: str
    wm_items: int
    circuit_open: bool
    outbox_pending: int


class MemoryBatchWriteItem(BaseModel):
    key: str = Field(..., min_length=1)
    value: Dict[str, Any] = Field(..., description="Payload stored in memory")
    meta: Optional[Dict[str, Any]] = Field(None, description="Optional metadata")
    ttl_seconds: Optional[int] = Field(None, ge=0, description="TTL override for this item")
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
    breaker_open: bool = False
    queued: int = 0


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


def _count_outbox_entries(memsvc: MemoryService) -> int:
    try:
        client = memsvc.client()
        path = getattr(client, "_outbox_path", None)
        if not path:
            return 0
        if not os.path.exists(path):
            return 0
        with open(path, "r", encoding="utf-8") as handle:
            return sum(1 for line in handle if line.strip())
    except Exception:
        return 0


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
    stored_payload.setdefault("memory_type", stored_payload.get("memory_type", "episodic"))
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
            attachment.dict(exclude_none=True)
            for attachment in attachments
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


@router.post("/remember", response_model=MemoryWriteResponse)
async def remember_memory(payload: MemoryWriteRequest, request: Request) -> MemoryWriteResponse:
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
        breaker_state = memsvc._is_circuit_open()
        raise HTTPException(
            status_code=503,
            detail={"message": str(exc), "breaker_open": breaker_state},
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"store failed: {exc}") from exc

    promoted_to_wm = False
    warnings: List[str] = []
    try:
        vec = np.asarray(embedder.embed(seed_text), dtype=np.float32)
        wm.admit(payload.tenant, vec, stored_payload)
        promoted_to_wm = True
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

    return MemoryWriteResponse(
        ok=True,
        tenant=payload.tenant,
        namespace=payload.namespace,
        coordinate=_serialize_coord(coord),
        queued=False,
        breaker_open=breaker_state,
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
            breaker_open=memsvc._is_circuit_open(),
            queued=0,
        )

    try:
        coords = await memsvc.aremember_bulk(
            [(ctx["key"], ctx["payload"]) for ctx in item_contexts],
            universe=None,
        )
        persisted_to_ltm = True
    except RuntimeError as exc:
        breaker_state = memsvc._is_circuit_open()
        raise HTTPException(
            status_code=503,
            detail={"message": str(exc), "breaker_open": breaker_state},
        ) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"store failed: {exc}") from exc

    results: List[MemoryBatchWriteResult] = []
    persisted_to_ltm = True
    for idx, ctx in enumerate(item_contexts):
        raw_coord = coords[idx] if idx < len(coords) else None
        coordinate = _serialize_coord(raw_coord)
        if raw_coord is not None:
            try:
                ctx["payload"]["coordinate"] = raw_coord
            except Exception:
                pass

        promoted_to_wm = False
        if ctx["vector"] is not None:
            try:
                wm.admit(payload.tenant, ctx["vector"], ctx["payload"])
                promoted_to_wm = True
            except Exception as exc:
                ctx["warnings"].append(f"working-memory-admit-failed:{exc}")

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
        breaker_open=memsvc._is_circuit_open(),
        queued=0,
    )


@router.post("/recall", response_model=MemoryRecallResponse)
async def recall_memory(payload: MemoryRecallRequest) -> MemoryRecallResponse:
    layer = (payload.layer or "all").lower()
    if layer not in {"wm", "ltm", "all"}:
        raise HTTPException(status_code=400, detail="layer must be wm, ltm, or omitted")

    wm_hits: List[MemoryRecallItem] = []
    ltm_hits: List[MemoryRecallItem] = []
    start = time.perf_counter()

    if layer in {"wm", "all"}:
        try:
            embedder = _get_embedder()
            vec = np.asarray(embedder.embed(payload.query), dtype=np.float32)
            wm = _get_wm()
            stage_start = time.perf_counter()
            hits = wm.recall(payload.tenant, vec, top_k=payload.top_k)
            stage_dur = time.perf_counter() - stage_start
            try:
                from somabrain import metrics as M

                M.RECALL_WM_LAT.labels(cohort="memory_api").observe(stage_dur)
            except Exception:
                pass
            for score, item_payload in hits:
                if not isinstance(item_payload, dict):
                    continue
                wm_hits.append(
                    MemoryRecallItem(
                        layer="wm",
                        score=float(score) if score is not None else None,
                        payload=item_payload,
                        coordinate=_serialize_coord(item_payload.get("coordinate")),
                        source="working_memory",
                    )
                )
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
            breaker_state = memsvc._is_circuit_open()
            raise HTTPException(
                status_code=503,
                detail={"message": str(exc), "breaker_open": breaker_state},
            ) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"recall failed: {exc}") from exc
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
            ltm_hits.append(
                MemoryRecallItem(
                    layer="ltm",
                    score=float(score_val) if score_val is not None else None,
                    payload=payload_obj,
                    coordinate=_serialize_coord(coord),
                    source="long_term_memory",
                )
            )

    duration = time.perf_counter() - start
    try:
        observe_recall_latency(payload.namespace, duration)
    except Exception:
        pass

    results = wm_hits + ltm_hits
    return MemoryRecallResponse(
        tenant=payload.tenant,
        namespace=payload.namespace,
        results=results,
        wm_hits=len(wm_hits),
        ltm_hits=len(ltm_hits),
        duration_ms=round(duration * 1000.0, 3),
    )


@router.get("/metrics", response_model=MemoryMetricsResponse)
async def memory_metrics(
    tenant: str = Query(..., min_length=1),
    namespace: str = Query(..., min_length=1),
) -> MemoryMetricsResponse:
    pool = _get_memory_pool()
    wm = _get_wm()
    resolved_ns = _resolve_namespace(tenant, namespace)
    memsvc = MemoryService(pool, resolved_ns)
    memsvc._reset_circuit_if_needed()

    try:
        wm_items = len(wm.items(tenant))
    except Exception:
        wm_items = 0

    outbox_pending = _count_outbox_entries(memsvc)
    try:
        memsvc._update_outbox_metric(outbox_pending)
    except Exception:
        pass
    try:
        record_memory_snapshot(tenant, namespace, items=wm_items)
    except Exception:
        pass

    return MemoryMetricsResponse(
        tenant=tenant,
        namespace=namespace,
        wm_items=wm_items,
        circuit_open=memsvc._is_circuit_open(),
        outbox_pending=outbox_pending,
    )
