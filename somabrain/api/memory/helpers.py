"""Helper Functions for Memory API.

This module contains helper functions extracted from somabrain/api/memory_api.py
for better organization and testability.

Functions:
- _get_runtime: Lazy runtime module accessor
- _get_app_config: Get application configuration
- _get_embedder: Get embedder singleton
- _get_wm: Get working memory singleton
- _get_memory_pool: Get memory pool singleton
- _resolve_namespace: Construct fully-qualified namespace
- _serialize_coord: Convert coordinate to serializable list
- _compose_memory_payload: Compose complete memory payload
"""

from __future__ import annotations

import importlib.util
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

from ninja.errors import HttpError

from django.conf import settings
from somabrain.api.memory.models import (
    MemoryAttachment,
    MemoryLink,
    MemorySignalPayload,
)

logger = logging.getLogger(__name__)


def _get_runtime():
    """Lazy import of runtime module to access singletons.

    Returns:
        The runtime module containing embedder, mt_wm, mt_memory singletons,
        or None if not found.
    """
    try:
        import somabrain.runtime as rt

        # Initialize runtime singletons on first access
        if rt.mt_memory is None:
            rt.initialize_runtime()
        return rt
    except ImportError:
        pass

    # Fallback: search in loaded modules
    _runtime_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "runtime.py"
    )
    _spec = importlib.util.spec_from_file_location("somabrain.runtime_module", _runtime_path)
    if _spec and _spec.name in sys.modules:
        return sys.modules[_spec.name]
    for m in list(sys.modules.values()):
        try:
            mf = getattr(m, "__file__", "") or ""
            if mf.endswith(os.path.join("somabrain", "runtime.py")):
                return m
        except Exception:
            continue
    return None


def _get_app_config():
    """Retrieve the central configuration singleton.

    Mirrors the logic used in other modules: attempt to reuse an existing
    ``cfg`` attribute on the runtime module; if missing, fall back to the
    unified ``settings`` instance and store it for future calls.

    Returns:
        The application configuration object.
    """
    rt = _get_runtime()
    if rt is None:
        return settings
    cfg = getattr(rt, "cfg", None)
    if cfg is None:
        cfg = settings
        setattr(rt, "cfg", cfg)
    return cfg


def _get_embedder():
    """Retrieve the global embedder instance from the runtime module.

    Returns:
        The embedder instance for text-to-vector conversion.

    Raises:
        HTTPException: 503 if embedder is not initialized.
    """
    rt = _get_runtime()
    embedder = getattr(rt, "embedder", None) if rt else None
    if embedder is None:
        raise HttpError(503, "embedder unavailable")
    return embedder


def _get_wm():
    """Retrieve the global working memory instance from the runtime module.

    Returns:
        The multi-tenant working memory (mt_wm) instance.

    Raises:
        HTTPException: 503 if working memory is not initialized.
    """
    rt = _get_runtime()
    wm = getattr(rt, "mt_wm", None) if rt else None
    if wm is None:
        raise HttpError(503, "working memory unavailable")
    return wm


def _get_memory_pool():
    """Retrieve the global memory pool instance from the runtime module.

    Returns:
        The multi-tenant memory pool (mt_memory) instance.

    Raises:
        HTTPException: 503 if memory pool is not initialized.
    """
    rt = _get_runtime()
    pool = getattr(rt, "mt_memory", None) if rt else None
    if pool is None:
        raise HttpError(503, "memory pool unavailable")
    return pool


def _resolve_namespace(tenant: str, namespace: str) -> str:
    """Construct a fully-qualified namespace string for memory operations.

    Args:
        tenant: Tenant identifier; defaults to 'public' if empty.
        namespace: Logical namespace within the tenant scope.

    Returns:
        Colon-separated namespace string in format 'base:tenant:namespace'.
    """
    base = getattr(_get_app_config(), "namespace", "somabrain")
    tenant_part = tenant.strip() or "public"
    ns_part = namespace.strip()
    core = f"{base}:{tenant_part}"
    return f"{core}:{ns_part}" if ns_part else core


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
) -> Tuple[Dict[str, Any], Dict[str, Any], str]:
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


__all__ = [
    "_get_runtime",
    "_get_app_config",
    "_get_embedder",
    "_get_wm",
    "_get_memory_pool",
    "_resolve_namespace",
    "_serialize_coord",
    "_compose_memory_payload",
    "_as_float_list",
    "_map_retrieval_to_memory_items",
    "_coerce_to_retrieval_request",
]


def _as_float_list(coord: object) -> Optional[List[float]]:
    """Convert coordinate to a list of floats.

    Handles list/tuple and comma-separated string formats.

    Args:
        coord: Coordinate in various formats (list, tuple, or comma-separated string).

    Returns:
        List of 3 floats if conversion succeeds, None otherwise.
    """
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


def _map_retrieval_to_memory_items(
    candidates: List[dict],
    MemoryRecallItem,
) -> List:
    """Map retrieval candidates to MemoryRecallItem instances.

    Args:
        candidates: List of candidate dictionaries from retrieval pipeline.
        MemoryRecallItem: The MemoryRecallItem class to instantiate.

    Returns:
        List of MemoryRecallItem instances.
    """
    items = []
    for c in candidates:
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
    obj: object,
    default_top_k: int,
    RetrievalRequest,
    MemoryRecallRequest,
):
    """Coerce various input types to a RetrievalRequest.

    Handles string queries, MemoryRecallRequest objects, and dict payloads.
    Applies environment-backed defaults for retrieval configuration.

    Args:
        obj: Input object (string, MemoryRecallRequest, or dict).
        default_top_k: Default top_k value if not specified.
        RetrievalRequest: The RetrievalRequest class to instantiate.
        MemoryRecallRequest: The MemoryRecallRequest class for type checking.

    Returns:
        RetrievalRequest instance with appropriate defaults applied.
    """

    def _env(name: str, default: str | None = None) -> str | None:
        """Execute env.

        Args:
            name: The name.
            default: The default.
        """

        try:
            v = getattr(settings, name.lower(), None)
            return v if v is not None and v != "" else default
        except Exception:
            return default

    def _env_bool(name: str, default: bool) -> bool:
        """Execute env bool.

        Args:
            name: The name.
            default: The default.
        """

        v = _env(name)
        if v is None:
            return default
        s = v.strip().lower()
        return s in ("1", "true", "yes", "on")

    full_power = _env_bool("SOMABRAIN_RECALL_FULL_POWER", True)
    simple_defaults = _env_bool("SOMABRAIN_RECALL_SIMPLE_DEFAULTS", False)

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

    if isinstance(obj, str):
        req = RetrievalRequest(query=obj, top_k=default_top_k)
        req.rerank = eff_rerank or req.rerank
        req.persist = (
            eff_persist if req.persist is None or isinstance(req.persist, bool) else req.persist
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
        req.rerank = eff_rerank or req.rerank
        req.persist = (
            eff_persist if req.persist is None or isinstance(req.persist, bool) else req.persist
        )
        if not req.retrievers:
            req.retrievers = eff_retrievers or req.retrievers
        return req

    if isinstance(obj, dict):
        d = dict(obj)
        q = d.get("query") or d.get("q") or ""
        rk = d.get("rerank")
        retr = d.get("retrievers")
        mode = d.get("mode")
        idv = d.get("id")
        keyv = d.get("key")
        coord = d.get("coord")
        uni = d.get("universe")
        tk = int(d.get("top_k") or default_top_k)
        # Use class field defaults directly instead of instantiating empty RetrievalRequest
        # (RetrievalRequest requires 'query' field, so RetrievalRequest() would fail)
        default_retrievers = RetrievalRequest.model_fields["retrievers"].default
        default_rerank = RetrievalRequest.model_fields["rerank"].default
        default_persist = RetrievalRequest.model_fields["persist"].default
        req = RetrievalRequest(
            query=str(q),
            top_k=tk,
            retrievers=(list(retr) if isinstance(retr, list) else default_retrievers),
            rerank=str(rk) if isinstance(rk, str) else default_rerank,
            persist=(bool(d.get("persist")) if d.get("persist") is not None else default_persist),
            universe=str(uni) if isinstance(uni, str) else None,
            mode=str(mode) if isinstance(mode, str) else None,
            id=str(idv) if isinstance(idv, str) else None,
            key=str(keyv) if isinstance(keyv, str) else None,
            coord=str(coord) if isinstance(coord, str) else None,
        )
        if not isinstance(retr, list) or not retr:
            req.retrievers = eff_retrievers or req.retrievers
        if not isinstance(rk, str) or not rk:
            req.rerank = eff_rerank or req.rerank
        if d.get("persist") is None:
            req.persist = eff_persist
        return req

    req = RetrievalRequest(query=str(obj), top_k=default_top_k)
    req.rerank = eff_rerank or req.rerank
    req.persist = (
        eff_persist if req.persist is None or isinstance(req.persist, bool) else req.persist
    )
    if not req.retrievers:
        req.retrievers = eff_retrievers or req.retrievers
    return req
