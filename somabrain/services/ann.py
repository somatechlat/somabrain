"""Cleanup index implementations (simple cosine + optional HNSW)."""

from __future__ import annotations

import threading
from dataclasses import dataclass, replace
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np

from somabrain.memory.superposed_trace import CleanupIndex


@dataclass
class AnnConfig:
    """Configuration for ANN cleanup indexes.

    Supported backends:
    - "milvus": Milvus vector database (default, scalable, persistent, recommended for production)
    - "hnsw": HNSW index via hnswlib (fast, in-memory)
    - "simple": In-memory cosine search (fallback only)

    Configuration is loaded from settings by default. Override via constructor
    for testing or custom deployments.
    """

    backend: str = "milvus"  # "milvus", "hnsw", or "simple"
    top_k: int = 64
    hnsw_m: int = 32
    hnsw_ef_construction: int = 200
    hnsw_ef_search: int = 128

    def with_updates(self, **kwargs: object) -> "AnnConfig":
        return replace(self, **kwargs)

    @classmethod
    def from_settings(cls) -> "AnnConfig":
        """Create AnnConfig from centralized settings."""
        from common.config.settings import settings

        return cls(
            backend=settings.tiered_memory_cleanup_backend,
            top_k=settings.tiered_memory_cleanup_topk,
            hnsw_m=settings.tiered_memory_cleanup_hnsw_m,
            hnsw_ef_construction=settings.tiered_memory_cleanup_hnsw_ef_construction,
            hnsw_ef_search=settings.tiered_memory_cleanup_hnsw_ef_search,
        )


class SimpleAnnIndex(CleanupIndex):
    """Naive cosine search over stored vectors. Deterministic and thread-safe."""

    def __init__(self, dim: int) -> None:
        self._dim = int(dim)
        self._vectors: Dict[str, np.ndarray] = {}
        self._lock = threading.Lock()

    def upsert(self, anchor_id: str, vector: np.ndarray) -> None:
        vec = _normalize(vector, self._dim)
        with self._lock:
            self._vectors[anchor_id] = vec

    def remove(self, anchor_id: str) -> None:
        with self._lock:
            self._vectors.pop(anchor_id, None)

    def search(self, query: np.ndarray, top_k: int) -> List[Tuple[str, float]]:
        vec = _normalize(query, self._dim)
        with self._lock:
            scores = [
                (anchor_id, float(np.dot(vec, stored)))
                for anchor_id, stored in self._vectors.items()
            ]
        scores.sort(key=lambda item: item[1], reverse=True)
        return scores[: max(0, int(top_k))]

    def configure(
        self, *, top_k: Optional[int] = None, ef_search: Optional[int] = None
    ) -> None:
        # Simple backend does not require tuning.
        return None


class HNSWAnnIndex(CleanupIndex):
    """Thin wrapper around hnswlib; falls back to SimpleAnnIndex if library missing."""

    def __init__(
        self, dim: int, *, m: int, ef_construction: int, ef_search: int
    ) -> None:
        try:
            import hnswlib  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("hnswlib not available") from exc

        self._dim = int(dim)
        self._index = hnswlib.Index(space="cosine", dim=self._dim)
        self._index.init_index(
            max_elements=200000, ef_construction=ef_construction, M=m
        )
        self._index.set_ef(ef_search)
        self._lock = threading.Lock()
        self._id_counter = 0
        self._ids: Dict[str, int] = {}
        self._deleted: Dict[str, int] = {}

    def upsert(self, anchor_id: str, vector: np.ndarray) -> None:
        vec = _normalize(vector, self._dim)
        arr = vec.reshape(1, -1)
        with self._lock:
            if anchor_id in self._ids:
                self._index.mark_deleted(self._ids[anchor_id])
            idx = self._id_counter
            self._id_counter += 1
            self._index.add_items(arr, ids=np.array([idx], dtype=np.int32))
            self._ids[anchor_id] = idx

    def remove(self, anchor_id: str) -> None:
        with self._lock:
            idx = self._ids.pop(anchor_id, None)
            if idx is not None:
                self._index.mark_deleted(idx)

    def search(self, query: np.ndarray, top_k: int) -> List[Tuple[str, float]]:
        vec = _normalize(query, self._dim)
        k = max(1, int(top_k))
        with self._lock:
            if not self._ids:
                return []
            labels, distances = self._index.knn_query(vec.reshape(1, -1), k=k)
            label_list = labels[0]
            dist_list = distances[0]
            inv_map = {idx: anchor for anchor, idx in self._ids.items()}
            results: List[Tuple[str, float]] = []
            for idx, dist in zip(label_list, dist_list):
                anchor = inv_map.get(int(idx))
                if anchor is None:
                    continue
                # hnswlib returns cosine distance -> convert to similarity
                score = float(1.0 - dist)
                results.append((anchor, score))
        results.sort(key=lambda item: item[1], reverse=True)
        return results[:k]

    def configure(
        self, *, top_k: Optional[int] = None, ef_search: Optional[int] = None
    ) -> None:
        if ef_search is None:
            return
        with self._lock:
            try:
                self._index.set_ef(int(ef_search))
            except Exception:
                pass


def create_cleanup_index(
    dim: int,
    cfg: Optional[AnnConfig] = None,
    *,
    tenant_id: str = "default",
    namespace: str = "cleanup",
) -> CleanupIndex:
    """Create a CleanupIndex based on configuration.

    Supported backends:
    - "milvus": Milvus vector database (default, recommended for production)
    - "hnsw": HNSW index via hnswlib
    - "simple": In-memory cosine search (fallback only)

    Configuration is loaded from settings if not provided explicitly.
    """
    config = cfg or AnnConfig.from_settings()
    backend = (config.backend or "milvus").lower()

    if backend == "milvus":
        try:
            from somabrain.services.milvus_ann import MilvusAnnIndex

            return MilvusAnnIndex(
                dim,
                tenant_id=tenant_id,
                namespace=namespace,
                top_k=config.top_k,
                ef_search=config.hnsw_ef_search,
            )
        except Exception:
            # Fall back to HNSW if Milvus unavailable
            backend = "hnsw"

    if backend == "hnsw":
        try:
            return HNSWAnnIndex(
                dim,
                m=config.hnsw_m,
                ef_construction=config.hnsw_ef_construction,
                ef_search=config.hnsw_ef_search,
            )
        except Exception:
            # Fall back to simple if hnsw unavailable
            return SimpleAnnIndex(dim)

    return SimpleAnnIndex(dim)


def _normalize(vec: np.ndarray | Iterable[float], dim: int) -> np.ndarray:
    arr = np.asarray(vec, dtype=np.float32).reshape(-1)
    if arr.shape[0] != dim:
        raise ValueError(f"vector must have dimension {dim}, got {arr.shape[0]}")
    norm = float(np.linalg.norm(arr))
    if norm <= 0.0:
        return np.zeros((dim,), dtype=np.float32)
    return (arr / norm).astype(np.float32, copy=False)


__all__ = [
    "AnnConfig",
    "CleanupIndex",
    "SimpleAnnIndex",
    "HNSWAnnIndex",
    "create_cleanup_index",
]
