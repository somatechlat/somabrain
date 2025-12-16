"""Remember Endpoints for Memory API.

This module contains the remember (write) endpoints extracted from memory_api.py
for better organization and to keep the main API file under 500 lines.

Endpoints:
- POST /memory/remember - Store a single memory
- POST /memory/remember/batch - Store multiple memories in batch
"""

from __future__ import annotations

import copy
import logging
import uuid
from typing import Any, Dict, List, Optional

import numpy as np
from fastapi import APIRouter, HTTPException, Request

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
from somabrain.runtime.config_runtime import (
    ensure_config_dispatcher,
    ensure_supervisor_worker,
)

logger = logging.getLogger(__name__)

# Router for remember endpoints - will be included by memory_api.py
router = APIRouter()


async def _ensure_config_runtime_started() -> None:
    """Ensure config runtime is started."""
    await ensure_config_dispatcher()
    await ensure_supervisor_worker()


def create_remember_endpoints(tiered_registry: TieredMemoryRegistry) -> APIRouter:
    """Create remember endpoints with the given tiered registry.

    Args:
        tiered_registry: The TieredMemoryRegistry instance to use for tiered storage.

    Returns:
        APIRouter with remember endpoints configured.
    """

    @router.post("/remember", response_model=MemoryWriteResponse)
    async def remember_memory(
        payload: MemoryWriteRequest, request: Request
    ) -> MemoryWriteResponse:
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
            memsvc._queue_degraded(
                "remember", {"key": payload.key, "payload": stored_payload}
            )
            degraded_warnings.append("memory-backend-unavailable:queued-for-replay")
        else:
            try:
                coord = await memsvc.aremember(payload.key, stored_payload)
                persisted_to_ltm = True
            except RuntimeError as exc:
                # Circuit just opened - queue locally
                memsvc._queue_degraded(
                    "remember", {"key": payload.key, "payload": stored_payload}
                )
                degraded_warnings.append(
                    f"memory-backend-failed:queued-for-replay:{exc}"
                )
            except Exception as exc:
                raise HTTPException(
                    status_code=502, detail=f"store failed: {exc}"
                ) from exc

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
            tiered_registry.remember(
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
                tiered_registry.remember(
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

    return router


__all__ = ["create_remember_endpoints", "router"]
