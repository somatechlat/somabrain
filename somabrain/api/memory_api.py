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
from threading import RLock
from typing import Any, Dict, List, Optional, Tuple, Annotated

import numpy as np

logger = logging.getLogger(__name__)
from fastapi import APIRouter, HTTPException, Query, Request, Body
from pydantic import BaseModel, Field

from somabrain.core.container import container

# Import Pydantic models from extracted module
from somabrain.api.memory.models import (
    MemoryAttachment,
    MemoryLink,
    MemorySignalPayload,
    MemorySignalFeedback,
    MemoryWriteRequest,
    MemoryWriteResponse,
    MemoryRecallRequest,
    MemoryRecallItem,
    MemoryRecallResponse,
    MemoryMetricsResponse,
    MemoryBatchWriteItem,
    MemoryBatchWriteRequest,
    MemoryBatchWriteResult,
    MemoryBatchWriteResponse,
    MemoryRecallSessionResponse,
    OutboxEventSummary,
    OutboxReplayRequest,
    AnnRebuildRequest,
)
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
)

# Unified configuration: use the central Settings instance from common.config.settings.
from common.config.settings import settings

# Use the new TenantManager for tenant resolution.
from somabrain.auth import require_auth, require_admin_auth
from somabrain.schemas import RetrievalRequest
from somabrain.db import outbox as outbox_db

router = APIRouter(prefix="/memory", tags=["memory"])


class RecallSessionStore:
    """Thread-safe store for recall sessions with TTL-based expiration.
    
    This class encapsulates the session management logic that was previously
    using module-level global state. Sessions are stored in-memory with
    automatic pruning of expired entries.
    
    Thread Safety:
        All operations are protected by a reentrant lock to ensure thread safety.
    """
    
    def __init__(self, ttl_seconds: int = 900) -> None:
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self._lock = RLock()
        self._ttl_seconds = ttl_seconds
    
    def store(
        self,
        session_id: str,
        tenant: str,
        namespace: str,
        conversation_id: Optional[str],
        scoring_mode: Optional[str],
        results: List[Any],
    ) -> None:
        """Store a recall session with results."""
        payload = {
            "session_id": session_id,
            "tenant": tenant,
            "namespace": namespace,
            "conversation_id": conversation_id,
            "scoring_mode": scoring_mode,
            "created_at": time.time(),
            "results": [item.dict() if hasattr(item, "dict") else item for item in results],
        }
        with self._lock:
            self._sessions[session_id] = payload
    
    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a session by ID, or None if not found."""
        with self._lock:
            return self._sessions.get(session_id)
    
    def prune(self) -> None:
        """Remove expired sessions."""
        now = time.time()
        with self._lock:
            expired = [
                session_id
                for session_id, state in self._sessions.items()
                if now - state.get("created_at", 0.0) > self._ttl_seconds
            ]
            for session_id in expired:
                self._sessions.pop(session_id, None)
    
    def clear(self) -> None:
        """Clear all sessions (for testing)."""
        with self._lock:
            self._sessions.clear()


def _create_recall_session_store() -> RecallSessionStore:
    """Factory function for DI container registration."""
    return RecallSessionStore(ttl_seconds=900)


container.register("recall_session_store", _create_recall_session_store)


def get_recall_session_store() -> RecallSessionStore:
    """Get the recall session store from the DI container."""
    return container.get("recall_session_store")


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
    except Exception as e:
        logger.debug("Failed to record memory snapshot for config event: %s", e)


register_config_listener(_handle_config_event)


async def _ensure_config_runtime_started() -> None:
    await ensure_config_dispatcher()
    await ensure_supervisor_worker()


# Pydantic models moved to somabrain/api/memory/models.py
# Imports: MemoryAttachment, MemoryLink, MemorySignalPayload, MemorySignalFeedback,
#          MemoryWriteRequest, MemoryWriteResponse, MemoryRecallRequest, MemoryRecallItem,
#          MemoryRecallResponse, MemoryMetricsResponse, MemoryBatchWriteItem,
#          MemoryBatchWriteRequest, MemoryBatchWriteResult, MemoryBatchWriteResponse,
#          MemoryRecallSessionResponse


def _tiered_enabled() -> bool:
    # Centralized feature gating with legacy env compatibility handled in modes
    from somabrain.modes import feature_enabled

    return feature_enabled("tiered_memory")


def _app_config():
    """Retrieve the central configuration singleton.

    Mirrors the logic used in other modules: attempt to reuse an existing
    ``cfg`` attribute on the runtime module; if missing, fall back to the
    unified ``settings`` instance and store it for future calls.
    """
    rt = _runtime_module()
    cfg = getattr(rt, "cfg", None)
    if cfg is None:
        cfg = settings
        setattr(rt, "cfg", cfg)
    return cfg


def _resolve_namespace(tenant: str, namespace: str) -> str:
    """Construct a fully-qualified namespace string for memory operations.
    
    Args:
        tenant: Tenant identifier; defaults to 'public' if empty.
        namespace: Logical namespace within the tenant scope.
    
    Returns:
        Colon-separated namespace string in format 'base:tenant:namespace'.
    """
    base = getattr(_app_config(), "namespace", "somabrain")
    tenant_part = tenant.strip() or "public"
    ns_part = namespace.strip()
    core = f"{base}:{tenant_part}"
    return f"{core}:{ns_part}" if ns_part else core


def _get_embedder():
    """Retrieve the global embedder instance from the runtime module.
    
    Returns:
        The embedder instance for text-to-vector conversion.
    
    Raises:
        HTTPException: 503 if embedder is not initialized.
    """
    embedder = getattr(_runtime_module(), "embedder", None)
    if embedder is None:
        raise HTTPException(status_code=503, detail="embedder unavailable")
    return embedder


def _get_wm():
    """Retrieve the global working memory instance from the runtime module.
    
    Returns:
        The multi-tenant working memory (mt_wm) instance.
    
    Raises:
        HTTPException: 503 if working memory is not initialized.
    """
    wm = getattr(_runtime_module(), "mt_wm", None)
    if wm is None:
        raise HTTPException(status_code=503, detail="working memory unavailable")
    return wm


def _get_memory_pool():
    """Retrieve the global memory pool instance from the runtime module.
    
    Returns:
        The multi-tenant memory pool (mt_memory) instance.
    
    Raises:
        HTTPException: 503 if memory pool is not initialized.
    """
    pool = getattr(_runtime_module(), "mt_memory", None)
    if pool is None:
        raise HTTPException(status_code=503, detail="memory pool unavailable")
    return pool


def _serialize_coord(coord: Any) -> Optional[List[float]]:
    """Convert a coordinate tuple to a serializable list of floats.
    
    Args:
        coord: A 3-element tuple or list representing spatial coordinates.
    
    Returns:
        List of 3 floats if conversion succeeds, None otherwise.
    """
    if isinstance(coord, (list, tuple)) and len(coord) == 3:
        try:
            return [float(coord[0]), float(coord[1]), float(coord[2])]
        except Exception:
            return None
    return None


# Removed: no local outbox support


def _prune_sessions() -> None:
    """Prune expired recall sessions from the store."""
    get_recall_session_store().prune()


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
    """Compose a complete memory payload from request parameters.
    
    Merges the provided value with metadata, tags, attachments, links, and
    signal data to create a fully-formed payload ready for storage.
    
    Args:
        tenant: Tenant identifier for the memory.
        namespace: Logical namespace within the tenant.
        key: Unique key for the memory entry.
        value: Core payload data to store.
        meta: Optional metadata to merge into the payload.
        universe: Universe scope (defaults to 'real' if not provided).
        attachments: List of attachment descriptors.
        links: List of outbound links to other memories.
        tags: Agent-supplied tags for categorization.
        policy_tags: Governance/policy tags for access control.
        signals: Agent-provided signals (importance, novelty, etc.).
        importance: Shortcut for signals.importance.
        novelty: Shortcut for signals.novelty.
        ttl_seconds: Time-to-live hint for automatic cleanup.
        trace_id: Correlation identifier for observability.
        actor: Identity of the actor performing the write.
    
    Returns:
        Tuple of (stored_payload, signal_data, seed_text) where:
        - stored_payload: Complete payload ready for storage
        - signal_data: Extracted signal information
        - seed_text: Text to use for embedding generation
    """
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
    """Store a recall session with results."""
    get_recall_session_store().store(
        session_id=session_id,
        tenant=tenant,
        namespace=namespace,
        conversation_id=conversation_id,
        scoring_mode=scoring_mode,
        results=results,
    )


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
    memsvc._is_circuit_open()

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
    except Exception as e:
        logger.debug("Failed to get WM items count: %s", e)
        items = 0
    try:
        record_memory_snapshot(payload.tenant, payload.namespace, items=items)
    except Exception as e:
        logger.debug("Failed to record memory snapshot: %s", e)

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
            except Exception as e:
                logger.debug("Failed to set coordinate on payload: %s", e)

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
    except Exception as e:
        logger.debug("Failed to get WM items count for batch: %s", e)
        items = 0
    try:
        record_memory_snapshot(payload.tenant, payload.namespace, items=items)
    except Exception as e:
        logger.debug("Failed to record memory snapshot for batch: %s", e)

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
            except Exception as e:
                logger.debug("Failed to record WM recall latency metric: %s", e)
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
        except Exception as e:
            logger.warning("WM recall failed: %s", e)

    if layer in {"ltm", "all"}:
        pool = _get_memory_pool()
        resolved_ns = _resolve_namespace(payload.tenant, payload.namespace)
        memsvc = MemoryService(pool, resolved_ns)
        stage_start = time.perf_counter()
        try:
            hits = await memsvc.arecall(
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
        except Exception as e:
            logger.debug("Failed to record LTM recall latency metric: %s", e)
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
    except Exception as e:
        logger.debug("Failed to observe recall latency: %s", e)

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
        except Exception as e:
            logger.debug("Failed to record tiered memory snapshot: %s", e)

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
    except Exception as e:
        logger.debug("Failed to submit metrics snapshot: %s", e)

    # Cutover functionality has been removed; shadow metrics are no longer recorded.

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


def _coerce_to_retrieval_request(
    obj: object, default_top_k: int = 10
) -> RetrievalRequest:
    # Resolve environment-backed defaults for full-power behavior with safe rollback
    def _env(name: str, default: str | None = None) -> str | None:
        try:
            # Retrieve configuration via attribute lookup; fallback to None.
            v = getattr(settings, name.lower(), None)
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
            _env("SOMABRAIN_RECALL_DEFAULT_RETRIEVERS", "vector,wm,graph") or ""
        ).split(",")
    else:
        eff_rerank = _env("SOMABRAIN_RECALL_DEFAULT_RERANK", "auto")
        eff_persist = _env_bool("SOMABRAIN_RECALL_DEFAULT_PERSIST", True)
        eff_retrievers = (
            _env("SOMABRAIN_RECALL_DEFAULT_RETRIEVERS", "vector,wm,graph,lexical") or ""
        ).split(",")
    eff_retrievers = [r.strip() for r in eff_retrievers if r and r.strip()]

    # Accept string or dict-like (including MemoryRecallRequest dict)
    if isinstance(obj, str):
        req = RetrievalRequest(query=obj, top_k=default_top_k)
        # Apply env-backed defaults when caller did not specify
        req.rerank = eff_rerank or req.rerank
        req.persist = (
            eff_persist
            if req.persist is None or isinstance(req.persist, bool)
            else req.persist
        )
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
        req.persist = (
            eff_persist
            if req.persist is None or isinstance(req.persist, bool)
            else req.persist
        )
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
            retrievers=(
                list(retr) if isinstance(retr, list) else RetrievalRequest().retrievers
            ),
            rerank=str(rk) if isinstance(rk, str) else RetrievalRequest().rerank,
            persist=(
                bool(d.get("persist"))
                if d.get("persist") is not None
                else RetrievalRequest().persist
            ),
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
    # Alternative: stringify unknown payload
    req = RetrievalRequest(query=str(obj), top_k=default_top_k)
    req.rerank = eff_rerank or req.rerank
    req.persist = (
        eff_persist
        if req.persist is None or isinstance(req.persist, bool)
        else req.persist
    )
    if not req.retrievers:
        req.retrievers = eff_retrievers or req.retrievers
    return req


@router.post("/recall", response_model=MemoryRecallResponse)
async def recall_memory(
    payload: Annotated[Any, Body(...)], request: Request
) -> MemoryRecallResponse:
    """Unified recall endpoint backed by the retrieval pipeline.

    Accepts either a plain string (JSON string) or an object body. For object bodies,
    accepts the legacy MemoryRecallRequest fields as well as RetrievalRequest fields.
    """
    await _ensure_config_runtime_started()
    cfg = settings
    ctx = await get_tenant_async(request, cfg.namespace)
    require_auth(request, cfg)
    from somabrain.infrastructure.cb_registry import get_cb

    cb = get_cb()
    degrade_readonly = bool(getattr(cfg, "memory_degrade_readonly", False))

    # Coerce incoming payload to a RetrievalRequest
    ret_req = _coerce_to_retrieval_request(payload, default_top_k=10)

    # If memory circuit is open, force WM-only retrieval and mark degraded
    circuit_open = cb.is_open(ctx.tenant_id) or cb.should_attempt_reset(ctx.tenant_id)
    degraded = False
    if circuit_open:
        degraded = True
        ret_req.retrievers = ["wm"]
        ret_req.persist = False
        # Avoid triggering external memory access in downstream pipeline
        ret_req.layer = "wm"
        if degrade_readonly:
            ret_req.retrievers = ["wm"]

    # Run pipeline
    import time as _time

    t0 = _time.perf_counter()
    from somabrain.services.retrieval_pipeline import run_retrieval_pipeline

    ret_resp = await run_retrieval_pipeline(
        ret_req,
        ctx=ctx,
        cfg=cfg,
        universe=ret_req.universe,
        trace_id=request.headers.get("X-Request-ID"),
    )
    dt_ms = round((_time.perf_counter() - t0) * 1000.0, 3)

    # Map candidates to MemoryRecallItems
    # Convert RetrievalResponse (pydantic) to dict for portability
    ret_dict = ret_resp.dict() if hasattr(ret_resp, "dict") else ret_resp
    cands = ret_dict.get("candidates") or []
    items = _map_retrieval_to_memory_items(cands)

    # Counts by retriever
    wm_hits = sum(1 for it in items if it.layer == "wm")
    ltm_hits = sum(1 for it in items if it.layer != "wm")

    # Metric: count recall requests (retrieval-backed)
    try:
        from somabrain import metrics as M

        M.RECALL_REQUESTS.labels(namespace=ctx.namespace).inc()
    except Exception as e:
        logger.debug("Failed to increment recall requests metric: %s", e)

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
        degraded=degraded,
    )


@router.post("/recall/stream", response_model=MemoryRecallResponse)
async def recall_memory_stream(
    payload: Annotated[Any, Body(...)], request: Request
) -> MemoryRecallResponse:
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
    except Exception as e:
        logger.debug("Failed to record memory snapshot for metrics endpoint: %s", e)

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


@router.get("/admin/outbox", response_model=List[OutboxEventSummary])
async def list_outbox_events(
    request: Request,
    status: str = Query(
        "failed",
        description="Outbox status filter (pending|failed|sent); defaults to 'failed'.",
    ),
    tenant: Optional[str] = Query(
        None, description="Optional tenant filter for outbox events."
    ),
    limit: int = Query(
        100, ge=1, le=500, description="Maximum number of events to return."
    ),
    offset: int = Query(
        0, ge=0, description="Offset into the result set for pagination."
    ),
) -> List[OutboxEventSummary]:
    """Admin-only listing of transactional outbox events.

    Uses the real DB outbox; there is no fake journal. This is intended for
    operational inspection of pending/failed events per tenant.
    """
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
        created_ts = None
        try:
            if ev.created_at is not None:
                created_ts = ev.created_at.timestamp()
        except Exception:
            created_ts = 0.0
        summaries.append(
            OutboxEventSummary(
                id=int(ev.id),
                tenant_id=ev.tenant_id,
                topic=ev.topic,
                status=ev.status,
                retries=int(ev.retries or 0),
                created_at=float(created_ts or 0.0),
                dedupe_key=str(ev.dedupe_key),
                last_error=ev.last_error,
                payload=ev.payload if isinstance(ev.payload, dict) else {},
            )
        )
    return summaries


@router.post("/admin/outbox/replay")
async def replay_outbox_events(
    request: Request, payload: OutboxReplayRequest
) -> Dict[str, Any]:
    """Admin-only API to mark failed/pending events for replay.

    This does not bypass the transactional outbox: it simply resets status
    to 'pending' so the outbox worker will reprocess them using the real
    Kafka pipeline.
    """
    cfg = getattr(request.app.state, "cfg", None)
    require_admin_auth(request, cfg)
    try:
        updated = outbox_db.mark_events_for_replay(payload.ids)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Replay failed: {exc}") from exc
    return {"ok": True, "updated": int(updated)}


# Cutover functionality has been fully removed per VIBE hardening.
# All related request/response models, helper functions, and endpoints have been deleted.
