"""Recall Operations for Memory API.

This module contains the core recall logic extracted from memory_api.py
for better organization and reduced file size.

Functions:
- _perform_recall: Core recall implementation with WM/LTM/tiered support
- _match_tags: Tag matching filter for candidates
- _within_age: Age-based filter for candidates
- _decorated_item: Create MemoryRecallItem from candidate
"""

from __future__ import annotations

import copy
import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from somabrain.api.memory.helpers import (
    _get_embedder,
    _get_memory_pool,
    _get_wm,
    _resolve_namespace,
    _serialize_coord,
)
from somabrain.api.memory.models import (
    MemoryRecallItem,
    MemoryRecallRequest,
    MemoryRecallResponse,
)
from somabrain.metrics import observe_recall_latency, record_memory_snapshot
from somabrain.core.runtime.config_runtime import (
    ensure_config_dispatcher,
    ensure_supervisor_worker,
    submit_metrics_snapshot,
)
from somabrain.services.memory_service import MemoryService
from somabrain.services.parameter_supervisor import MetricsSnapshot

logger = logging.getLogger(__name__)


def _get_tiered_registry():
    """Lazy import of tiered registry to avoid circular imports."""
    from somabrain.api.memory_api import _TIERED_REGISTRY

    return _TIERED_REGISTRY


def _tiered_enabled() -> bool:
    """Check if tiered memory feature is enabled."""
    from somabrain.runtime.modes import feature_enabled

    return feature_enabled("tiered_memory")


def _get_recall_session_store():
    """Get the recall session store from the DI container."""
    from somabrain.api.memory_api import get_recall_session_store

    return get_recall_session_store()


def _prune_sessions() -> None:
    """Prune expired recall sessions from the store."""
    _get_recall_session_store().prune()


def _store_recall_session(
    session_id: str,
    tenant: str,
    namespace: str,
    conversation_id: Optional[str],
    scoring_mode: Optional[str],
    results: List[MemoryRecallItem],
) -> None:
    """Store a recall session with results."""
    _get_recall_session_store().store(
        session_id=session_id,
        tenant=tenant,
        namespace=namespace,
        conversation_id=conversation_id,
        scoring_mode=scoring_mode,
        results=results,
    )


async def _ensure_config_runtime_started() -> None:
    """Ensure config runtime is started."""
    await ensure_config_dispatcher()
    await ensure_supervisor_worker()


def _match_tags(candidate: Dict[str, Any], required_tags: Optional[List[str]]) -> bool:
    """Check if candidate matches required tags."""
    if not required_tags:
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
    return all(tag in candidate_tags for tag in required_tags)


def _within_age(candidate: Dict[str, Any], max_age_seconds: Optional[float]) -> bool:
    """Check if candidate is within max age."""
    if max_age_seconds is None:
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
            return time.time() - ts <= max_age_seconds
        except Exception:
            continue
    return False


def _decorated_item(
    layer_name: str,
    source: str,
    score_val: Optional[float],
    candidate_payload: Dict[str, Any],
    coord_obj: Any,
    required_tags: Optional[List[str]],
    max_age_seconds: Optional[float],
    min_score: Optional[float],
) -> Optional[MemoryRecallItem]:
    """Create a decorated MemoryRecallItem from candidate data."""
    if not _match_tags(candidate_payload, required_tags):
        return None
    if not _within_age(candidate_payload, max_age_seconds):
        return None
    if min_score is not None and score_val is not None:
        if score_val < min_score:
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


async def perform_recall(
    payload: MemoryRecallRequest,
    *,
    default_chunk_size: Optional[int] = None,
) -> MemoryRecallResponse:
    """Perform memory recall across WM, LTM, and tiered memory.

    This is the core recall implementation that handles:
    - Working memory (WM) recall via embeddings
    - Long-term memory (LTM) recall via MemoryService
    - Tiered memory recall via TieredMemoryRegistry
    - Result filtering by tags, age, and score
    - Session management and chunking
    """
    from ninja.errors import HttpError

    await _ensure_config_runtime_started()
    layer = (payload.layer or "all").lower()
    if layer not in {"wm", "ltm", "all"}:
        raise HttpError(400, "layer must be wm, ltm, or omitted")

    chunk_size = payload.chunk_size or default_chunk_size
    chunk_index = payload.chunk_index if payload.chunk_index >= 0 else 0

    wm_hits: List[MemoryRecallItem] = []
    ltm_hits: List[MemoryRecallItem] = []
    start = time.perf_counter()

    # Get embedder and query vector
    embedder = None
    query_vec: Optional[np.ndarray] = None
    try:
        embedder = _get_embedder()
        query_vec = np.asarray(embedder.embed(payload.query), dtype=np.float32)
    except HttpError:
        if layer in {"wm", "all"}:
            raise
    except Exception:
        embedder = None
        query_vec = None

    # WM recall
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
                    payload.tags,
                    payload.max_age_seconds,
                    payload.min_score,
                )
                if item is not None:
                    wm_hits.append(item)
        except HttpError:
            raise
        except Exception as e:
            logger.warning("WM recall failed: %s", e)

    # LTM recall
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
            raise HttpError(503, str(exc)) from exc
        except Exception as exc:
            raise HttpError(502, f"recall failed: {exc}") from exc
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
                payload.tags,
                payload.max_age_seconds,
                payload.min_score,
            )
            if item is not None:
                ltm_hits.append(item)

    # Tiered memory recall
    tiered_item: Optional[MemoryRecallItem] = None
    tiered_margin_value: Optional[float] = None
    tiered_eta_value: Optional[float] = None
    tiered_sparsity_value: Optional[float] = None
    if _tiered_enabled() and query_vec is not None:
        try:
            tiered_registry = _get_tiered_registry()
            tiered_hit = tiered_registry.recall(
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
                payload.tags,
                payload.max_age_seconds,
                payload.min_score,
            )
            if item is not None:
                tiered_item = item
                tiered_margin_value = tiered_hit.context.margin
                tiered_eta_value = tiered_hit.eta
                tiered_sparsity_value = tiered_hit.sparsity

    # Deduplicate and merge results
    all_results: List[MemoryRecallItem] = []
    seen: set[Tuple[Optional[Tuple[float, ...]], str, str]] = set()

    def _append(item: Optional[MemoryRecallItem]) -> None:
        """Execute append.

        Args:
            item: The item.
        """

        if item is None:
            return
        coord_key = tuple(item.coordinate) if item.coordinate is not None else None
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

    # Apply chunking
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

    # Session management
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

    # Record tiered metrics
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

    # Submit metrics snapshot
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


__all__ = [
    "perform_recall",
    "_match_tags",
    "_within_age",
    "_decorated_item",
    "_prune_sessions",
    "_store_recall_session",
]
