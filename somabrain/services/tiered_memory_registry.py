"""Lightweight registry managing TieredMemory instances per tenant/namespace."""

from __future__ import annotations

import copy
import math
import os
import threading
from dataclasses import dataclass, replace
from typing import Dict, Optional, Tuple

import numpy as np

from somabrain.memory.hierarchical import LayerPolicy, RecallContext, TieredMemory
from somabrain.memory.superposed_trace import TraceConfig
from somabrain.services.ann import AnnConfig, create_cleanup_index
from somabrain.services.config_service import ConfigEvent


@dataclass
class _TieredBundle:
    memory: TieredMemory
    payloads: Dict[str, dict]
    coordinates: Dict[str, Optional[list]]
    lock: threading.Lock
    wm_cfg: TraceConfig
    ltm_cfg: TraceConfig
    wm_policy: LayerPolicy
    sparsity: float


@dataclass
class TieredRecallResult:
    """Container for recall data returned by the registry."""

    context: RecallContext
    payload: Optional[dict]
    coordinate: Optional[list]
    eta: float
    tau: float
    sparsity: float


class TieredMemoryRegistry:
    """Maintain TieredMemory instances keyed by (tenant, namespace)."""

    def __init__(self) -> None:
        self._bundles: Dict[Tuple[str, str], _TieredBundle] = {}
        self._lock = threading.Lock()

    def remember(
        self,
        tenant: str,
        namespace: str,
        *,
        anchor_id: str,
        key_vector: np.ndarray | list[float] | tuple[float, ...],
        value_vector: np.ndarray | list[float] | tuple[float, ...],
        payload: dict,
        coordinate: Optional[list],
    ) -> None:
        """Insert or update an anchor in the tiered memory registry."""

        if not anchor_id:
            return
        vec = _as_vector(key_vector)
        value_vec = _as_vector(value_vector)
        bundle = self._ensure_bundle(tenant, namespace, dim=vec.shape[0])
        with bundle.lock:
            bundle.memory.remember(anchor_id, vec, value_vec)
            bundle.payloads[anchor_id] = copy.deepcopy(payload)
            if coordinate is not None:
                bundle.coordinates[anchor_id] = list(coordinate)
            else:
                bundle.coordinates.pop(anchor_id, None)

    def recall(
        self,
        tenant: str,
        namespace: str,
        query_vector: np.ndarray | list[float] | tuple[float, ...],
    ) -> Optional[TieredRecallResult]:
        """Recall from tiered memory, returning context plus stored payload."""

        key = (tenant, namespace)
        bundle = self._bundles.get(key)
        if bundle is None:
            return None
        qvec = _as_vector(query_vector)
        with bundle.lock:
            if not bundle.payloads:
                return None
            context = bundle.memory.recall(qvec)
            if not context.anchor_id or context.score <= 0.0:
                return None
            payload = bundle.payloads.get(context.anchor_id)
            coordinate = bundle.coordinates.get(context.anchor_id)
            payload_copy = copy.deepcopy(payload) if payload is not None else None
            return TieredRecallResult(
                context=context,
                payload=payload_copy,
                coordinate=copy.deepcopy(coordinate) if coordinate is not None else None,
                eta=bundle.wm_cfg.eta,
                tau=bundle.wm_policy.threshold,
                sparsity=bundle.sparsity,
            )

    def _ensure_bundle(self, tenant: str, namespace: str, *, dim: int) -> _TieredBundle:
        key = (tenant, namespace)
        with self._lock:
            bundle = self._bundles.get(key)
            if bundle is None:
                ann_cfg = _ann_config_from_env()
                wm_cfg = TraceConfig(dim=dim, rotation_enabled=True, cleanup_topk=ann_cfg.top_k)
                ltm_cfg = TraceConfig(dim=dim, rotation_enabled=True, cleanup_topk=ann_cfg.top_k)
                tiered = TieredMemory(
                    wm_cfg,
                    ltm_cfg,
                    wm_cleanup_index=create_cleanup_index(wm_cfg.dim, ann_cfg),
                    ltm_cleanup_index=create_cleanup_index(ltm_cfg.dim, ann_cfg),
                )
                bundle = _TieredBundle(
                    memory=tiered,
                    payloads={},
                    coordinates={},
                    lock=threading.Lock(),
                    wm_cfg=wm_cfg,
                    ltm_cfg=ltm_cfg,
                    wm_policy=tiered.wm_policy,
                    sparsity=1.0,
                )
                self._bundles[key] = bundle
            return bundle

    def apply_effective_config(self, event: ConfigEvent) -> Optional[Dict[str, float]]:
        key = (event.tenant, event.namespace)
        bundle = self._bundles.get(key)
        if bundle is None:
            return None
        payload = event.payload or {}
        eta = _as_optional_float(_dig(payload, ("eta",), ("trace", "eta")))
        cleanup_topk = _as_optional_int(_dig(payload, ("cleanup", "topk")))
        sparsity = _as_optional_float(_dig(payload, ("sparsity",)))
        ef_search = _as_optional_int(_dig(payload, ("cleanup", "hnsw", "efSearch")))
        wm_tau = _as_optional_float(_dig(payload, ("gate", "tau")))
        cleanup_params = {}
        if ef_search is not None:
            cleanup_params["ef_search"] = ef_search

        with bundle.lock:
            bundle.memory.configure(
                wm_eta=eta,
                cleanup_topk=cleanup_topk,
                cleanup_params=cleanup_params or None,
                wm_tau=wm_tau,
            )
            if eta is not None:
                bundle.wm_cfg = replace(bundle.wm_cfg, eta=eta)
                bundle.ltm_cfg = replace(bundle.ltm_cfg, eta=eta)
            if cleanup_topk is not None and cleanup_topk > 0:
                bundle.wm_cfg = replace(bundle.wm_cfg, cleanup_topk=cleanup_topk)
                bundle.ltm_cfg = replace(bundle.ltm_cfg, cleanup_topk=cleanup_topk)
            if sparsity is not None and sparsity >= 0.0:
                bundle.sparsity = sparsity
            if wm_tau is not None and 0.0 <= wm_tau <= 1.0:
                try:
                    bundle.wm_policy = LayerPolicy(
                        threshold=wm_tau,
                        promote_margin=bundle.wm_policy.promote_margin,
                    ).validate()
                except Exception:
                    pass
            return {
                "eta": bundle.wm_cfg.eta,
                "sparsity": bundle.sparsity,
                "tau": bundle.wm_policy.threshold,
            }


def _as_vector(arr: np.ndarray | list[float] | tuple[float, ...]) -> np.ndarray:
    vec = np.asarray(arr, dtype=np.float32)
    if vec.ndim != 1:
        vec = vec.reshape(-1)
    return vec.astype(np.float32, copy=False)


def _dig(data: Dict, *paths: Tuple[str, ...]) -> Optional[object]:
    for path in paths:
        node = data
        found = True
        for part in path:
            if not isinstance(node, dict) or part not in node:
                found = False
                break
            node = node.get(part)
        if found:
            return node
    return None


def _as_optional_float(value: object) -> Optional[float]:
    if value is None:
        return None
    try:
        numeric = float(value)
    except Exception:
        return None
    if not math.isfinite(numeric):
        return None
    return numeric


def _as_optional_int(value: object) -> Optional[int]:
    if value is None:
        return None
    try:
        numeric = int(value)
    except Exception:
        return None
    return numeric


def _ann_config_from_env() -> AnnConfig:
    backend = os.getenv("SOMABRAIN_CLEANUP_BACKEND", "simple")
    try:
        top_k = int(os.getenv("SOMABRAIN_CLEANUP_TOPK", "64"))
    except Exception:
        top_k = 64
    try:
        m = int(os.getenv("SOMABRAIN_CLEANUP_HNSW_M", "32"))
    except Exception:
        m = 32
    try:
        ef_construction = int(os.getenv("SOMABRAIN_CLEANUP_HNSW_EF_CONSTRUCTION", "200"))
    except Exception:
        ef_construction = 200
    try:
        ef_search = int(os.getenv("SOMABRAIN_CLEANUP_HNSW_EF_SEARCH", "128"))
    except Exception:
        ef_search = 128
    return AnnConfig(
        backend=backend,
        top_k=top_k,
        hnsw_m=m,
        hnsw_ef_construction=ef_construction,
        hnsw_ef_search=ef_search,
    )


__all__ = ["TieredMemoryRegistry", "TieredRecallResult"]
