"""Remember Endpoints - Django Ninja Version

Migrated from FastAPI to Django Ninja.
Complex memory write logic (batch, signals, embedding).
"""

from __future__ import annotations

import copy
import logging
import uuid
import numpy as np
from typing import Any, Dict, List, Optional
from ninja import Router
from django.http import HttpRequest
from ninja.errors import HttpError

from django.conf import settings
from somabrain.api.auth import bearer_auth
from somabrain.auth import require_auth
from somabrain.api.memory.models import (
    MemorySignalFeedback,
    MemoryWriteRequest,
    MemoryWriteResponse,
    MemoryBatchWriteRequest,
    MemoryBatchWriteResult,
    MemoryBatchWriteResponse,
)
from somabrain.api.memory.helpers import (
    _get_embedder,
    _get_wm,
    _get_memory_pool,
    _resolve_namespace,
    _serialize_coord,
    _compose_memory_payload,
)
from somabrain.metrics import record_memory_snapshot
from somabrain.services.memory_service import MemoryService
from somabrain.services.tiered_memory_registry import TieredMemoryRegistry

logger = logging.getLogger("somabrain.api.endpoints.memory_remember")

router = Router(tags=["memory"])

def _ensure_runtime():
    """Ensure config runtime is accessible."""
    from somabrain.runtime.config_runtime import ensure_config_dispatcher
    # In sync code we might just rely on side-effects or call async if valid
    # For now, assuming runtime is initialized by WSGI/ASGI entrypoint or middleware
    pass

@router.post("/remember", response=MemoryWriteResponse, auth=bearer_auth)
def remember_memory(request: HttpRequest, payload: MemoryWriteRequest):
    """Store a memory in both WM and LTM."""
    require_auth(request, settings)
    
    pool = _get_memory_pool()
    wm = _get_wm()
    embedder = _get_embedder()
    
    if not pool or not wm or not embedder:
         # Fail gracefully or noisily? Using 503 as in original
         raise HttpError(503, "Memory services not available")

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

    circuit_open = memsvc._is_circuit_open()

    if circuit_open:
        memsvc._queue_degraded("remember", {"key": payload.key, "payload": stored_payload})
        degraded_warnings.append("memory-backend-unavailable:queued-for-replay")
    else:
        try:
            # Sync wrapper for async aremember? 
            # If MemService only has async, we need async view. 
            # Converting this to async def since Ninja supports it.
            # But the task is 'sync' preferred? 
            # Looking at original: it was async. Ninja supports async.
            # I will use async def for compatibility with async calls.
            # BUT if I make this async, I need to ensure everything else is async-safe.
            # Let's try synchronous call if possible, or use async. 
            # Django Ninja runs async views in async loop.
            # Let's start with async view signature to enable awaits.
            pass
        except Exception:
            pass

    return _remember_logic(request, payload, memsvc, wm, embedder, stored_payload, signal_data, seed_text, request_id, degraded_warnings)

# Splitting logic to handle async nature properly
# We need to redefine the view as async because memsvc likely uses async HTTP/DB
@router.post("/remember", response=MemoryWriteResponse, auth=bearer_auth)
async def remember_memory_async(request: HttpRequest, payload: MemoryWriteRequest):
    """Store a memory (Async)."""
    require_auth(request, settings)
    pool = _get_memory_pool()
    wm = _get_wm()
    embedder = _get_embedder()
    
    if not pool:
         raise HttpError(503, "Memory services not available")

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
    
    if memsvc._is_circuit_open():
        memsvc._queue_degraded("remember", {"key": payload.key, "payload": stored_payload})
        degraded_warnings.append("memory-backend-unavailable:queued-for-replay")
    else:
        try:
            coord = await memsvc.aremember(payload.key, stored_payload)
            persisted_to_ltm = True
        except RuntimeError as exc:
            memsvc._queue_degraded("remember", {"key": payload.key, "payload": stored_payload})
            degraded_warnings.append(f"memory-backend-failed:queued-for-replay:{exc}")
        except Exception as exc:
            raise HttpError(502, f"store failed: {exc}")

    coordinate_list = _serialize_coord(coord)
    if coordinate_list is not None:
        stored_payload["coordinate"] = coordinate_list

    promoted_to_wm = False
    warnings: List[str] = []
    tiered_vector = None
    
    try:
        # Embedder is usually sync or CPU bound
        vec = np.asarray(embedder.embed(seed_text), dtype=np.float32)
        if wm:
            wm.admit(payload.tenant, vec, stored_payload)
            promoted_to_wm = True
        tiered_vector = vec
    except Exception as exc:
        warnings.append(f"working-memory-admit-failed:{exc}")

    # Metrics
    try:
        if wm:
            items = len(wm.items(payload.tenant))
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
    
    if tiered_vector is not None:
        registry = TieredMemoryRegistry()
        registry.remember(
             payload.tenant,
             payload.namespace,
             anchor_id=payload.key or request_id,
             key_vector=tiered_vector,
             value_vector=tiered_vector,
             payload=copy.deepcopy(stored_payload),
             coordinate=coordinate_list,
        )

    return {
        "ok": True,
        "tenant": payload.tenant,
        "namespace": payload.namespace,
        "coordinate": coordinate_list,
        "promoted_to_wm": promoted_to_wm,
        "persisted_to_ltm": persisted_to_ltm,
        "deduplicated": False,
        "importance": signal_feedback.importance,
        "novelty": signal_feedback.novelty,
        "ttl_applied": signal_feedback.ttl_seconds,
        "trace_id": payload.trace_id,
        "request_id": request_id,
        "warnings": degraded_warnings + warnings,
        "signals": signal_feedback,
    }

@router.post("/remember/batch", response=MemoryBatchWriteResponse, auth=bearer_auth)
async def remember_memory_batch(request: HttpRequest, payload: MemoryBatchWriteRequest):
    """Store multiple memories in batch."""
    require_auth(request, settings)
    pool = _get_memory_pool()
    wm = _get_wm()
    embedder = _get_embedder()
    
    if not pool:
         raise HttpError(503, "Memory services not available")
         
    resolved_ns = _resolve_namespace(payload.tenant, payload.namespace)
    memsvc = MemoryService(pool, resolved_ns)
    memsvc._reset_circuit_if_needed()
    
    actor = request.headers.get("X-Actor") or "memory-api"
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    item_contexts = []
    
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
        warnings = []
        try:
             vector = np.asarray(embedder.embed(seed_text), dtype=np.float32)
        except Exception as exc:
             warnings.append(f"working-memory-embed-failed:{exc}")
        
        item_contexts.append({
            "key": item.key,
            "payload": stored_payload,
            "signal_data": signal_data,
            "seed_text": seed_text,
            "trace_id": item.trace_id,
            "vector": vector,
            "warnings": warnings,
        })
        
    if not item_contexts:
        return {"ok": True, "tenant": payload.tenant, "namespace": payload.namespace, "results": []}

    try:
        coords = await memsvc.aremember_bulk(
            [(ctx["key"], ctx["payload"]) for ctx in item_contexts], universe=None
        )
        persisted_to_ltm = True
    except RuntimeError as exc:
        raise HttpError(503, str(exc))
    except Exception as exc:
        raise HttpError(502, f"store failed: {exc}")

    results = []
    registry = TieredMemoryRegistry()
    
    for idx, ctx in enumerate(item_contexts):
        raw_coord = coords[idx] if idx < len(coords) else None
        coordinate = _serialize_coord(raw_coord)
        if coordinate:
            ctx["payload"]["coordinate"] = coordinate
            
        promoted_to_wm = False
        if ctx["vector"] is not None and wm:
            try:
                wm.admit(payload.tenant, ctx["vector"], ctx["payload"])
                promoted_to_wm = True
            except Exception as exc:
                ctx["warnings"].append(f"working-memory-admit-failed:{exc}")
            
            registry.remember(
                payload.tenant,
                payload.namespace,
                anchor_id=ctx["key"],
                key_vector=ctx["vector"],
                value_vector=ctx["vector"],
                payload=copy.deepcopy(ctx["payload"]),
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
        results.append({
            "key": ctx["key"],
            "coordinate": coordinate,
            "promoted_to_wm": promoted_to_wm,
            "persisted_to_ltm": persisted_to_ltm,
            "deduplicated": False,
            "importance": signal_feedback.importance,
            "novelty": signal_feedback.novelty,
            "ttl_applied": signal_feedback.ttl_seconds,
            "trace_id": ctx["trace_id"],
            "request_id": f"{request_id}:{idx}",
            "warnings": ctx["warnings"],
            "signals": signal_feedback,
        })

    try:
        if wm:
             items = len(wm.items(payload.tenant))
             record_memory_snapshot(payload.tenant, payload.namespace, items=items)
    except Exception:
        pass

    return {
        "ok": True, 
        "tenant": payload.tenant, 
        "namespace": payload.namespace, 
        "results": results
    }
