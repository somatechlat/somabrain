"""Milvus-backed ANN index for SomaBrain TieredMemory.

This module provides a CleanupIndex implementation that uses Milvus for
vector similarity search. It replaces the in-memory SimpleAnnIndex and
HNSWAnnIndex for production deployments where scalability is required.

VIBE CODING RULES:
- All configuration from common.config.settings
- No hardcoded values
- Real Milvus connection required; simulated connectors are not supported.
"""

from __future__ import annotations

import logging
import threading
from typing import Dict, List, Optional, Tuple

import numpy as np

from django.conf import settings
from somabrain.memory.superposed_trace import CleanupIndex

logger = logging.getLogger(__name__)

# Lazy import pymilvus to avoid import-time failures
_PYMILVUS_AVAILABLE = False
try:
    from pymilvus import (
        Collection,
        CollectionSchema,
        DataType,
        FieldSchema,
        connections,
        utility,
    )
    from pymilvus.exceptions import MilvusException

    _PYMILVUS_AVAILABLE = True
except ImportError:
    MilvusException = Exception


class MilvusAnnIndex(CleanupIndex):
    """Milvus-backed CleanupIndex for TieredMemory vector operations.

    This implementation uses Milvus for scalable vector similarity search,
    replacing the in-memory SimpleAnnIndex for production deployments.

    Configuration is read from settings:
    - milvus_host: Milvus server hostname
    - milvus_port: Milvus server port
    - milvus_collection: Collection name prefix (tenant-specific suffix added)
    """

    def __init__(
        self,
        dim: int,
        *,
        tenant_id: str = "default",
        namespace: str = "cleanup",
        top_k: int = 64,
        ef_search: int = 128,
    ) -> None:
        """Initialize the instance."""

        if not _PYMILVUS_AVAILABLE:
            raise RuntimeError(
                "pymilvus is required for MilvusAnnIndex. "
                "Install with: pip install pymilvus>=2.4"
            )

        self._dim = int(dim)
        self._tenant_id = tenant_id
        self._namespace = namespace
        self._top_k = top_k
        self._ef_search = ef_search
        self._lock = threading.Lock()

        # Collection name includes tenant and namespace for isolation
        self._collection_name = f"soma_{namespace}_{tenant_id}".replace("-", "_")

        # Connection parameters from settings
        self._host = settings.MILVUS_HOST or "localhost"
        self._port = settings.MILVUS_PORT or 19530

        # Local ID mapping for anchor_id -> Milvus internal ID
        self._anchor_to_id: Dict[str, int] = {}
        self._id_counter = 0

        # Initialize connection and collection
        self._collection: Optional[Collection] = None
        self._connect()

    def _connect(self) -> None:
        """Establish connection to Milvus and create collection if needed."""
        try:
            # Connect to Milvus
            connections.connect(
                alias="default",
                host=self._host,
                port=self._port,
            )
            logger.info(
                "Connected to Milvus at %s:%s for collection %s",
                self._host,
                self._port,
                self._collection_name,
            )

            # Create collection if it doesn't exist
            if not utility.has_collection(self._collection_name):
                self._create_collection()
            else:
                self._collection = Collection(self._collection_name)
                self._collection.load()

        except MilvusException as exc:
            logger.error("Failed to connect to Milvus: %s", exc)
            raise RuntimeError(f"Milvus connection failed: {exc}") from exc

    def _create_collection(self) -> None:
        """Create the Milvus collection with appropriate schema."""
        fields = [
            FieldSchema(
                name="id",
                dtype=DataType.INT64,
                is_primary=True,
                auto_id=False,
            ),
            FieldSchema(
                name="anchor_id",
                dtype=DataType.VARCHAR,
                max_length=512,
            ),
            FieldSchema(
                name="vector",
                dtype=DataType.FLOAT_VECTOR,
                dim=self._dim,
            ),
        ]
        schema = CollectionSchema(
            fields,
            description=f"SomaBrain cleanup index for {self._namespace}/{self._tenant_id}",
        )

        self._collection = Collection(self._collection_name, schema)

        # Create IVF_FLAT index for cosine similarity
        index_params = {
            "index_type": "IVF_FLAT",
            "metric_type": "COSINE",
            "params": {"nlist": 128},
        }
        self._collection.create_index(
            field_name="vector",
            index_params=index_params,
        )
        self._collection.load()

        logger.info(
            "Created Milvus collection %s with dim=%d",
            self._collection_name,
            self._dim,
        )

    def upsert(self, anchor_id: str, vector: np.ndarray) -> None:
        """Insert or update a vector for the given anchor ID."""
        if self._collection is None:
            raise RuntimeError("Milvus collection not initialized")

        vec = self._normalize(vector)

        with self._lock:
            # Check if anchor already exists
            if anchor_id in self._anchor_to_id:
                # Delete existing entry
                old_id = self._anchor_to_id[anchor_id]
                try:
                    self._collection.delete(f"id == {old_id}")
                except Exception as exc:
                    logger.warning(
                        "Failed to delete old vector for %s: %s", anchor_id, exc
                    )

            # Assign new ID
            new_id = self._id_counter
            self._id_counter += 1
            self._anchor_to_id[anchor_id] = new_id

            # Insert new vector
            entities = [
                [new_id],  # id
                [anchor_id],  # anchor_id
                [vec.tolist()],  # vector
            ]

            try:
                self._collection.insert(entities)
                self._collection.flush()
            except MilvusException as exc:
                logger.error("Failed to upsert vector for %s: %s", anchor_id, exc)
                raise

    def remove(self, anchor_id: str) -> None:
        """Remove a vector by anchor ID."""
        if self._collection is None:
            return

        with self._lock:
            if anchor_id not in self._anchor_to_id:
                return

            internal_id = self._anchor_to_id.pop(anchor_id)
            try:
                self._collection.delete(f"id == {internal_id}")
                self._collection.flush()
            except MilvusException as exc:
                logger.warning("Failed to remove vector for %s: %s", anchor_id, exc)

    def search(self, query: np.ndarray, top_k: int) -> List[Tuple[str, float]]:
        """Search for similar vectors and return (anchor_id, score) pairs."""
        if self._collection is None:
            return []

        vec = self._normalize(query)
        k = max(1, min(int(top_k), self._top_k))

        search_params = {
            "metric_type": "COSINE",
            "params": {"nprobe": min(16, self._ef_search // 8)},
        }

        try:
            results = self._collection.search(
                data=[vec.tolist()],
                anns_field="vector",
                param=search_params,
                limit=k,
                output_fields=["anchor_id"],
            )
        except MilvusException as exc:
            logger.error("Milvus search failed: %s", exc)
            return []

        output: List[Tuple[str, float]] = []
        if results and len(results) > 0:
            for hit in results[0]:
                anchor = hit.entity.get("anchor_id")
                # Milvus returns distance; for COSINE metric, similarity = 1 - distance
                # But with COSINE metric_type, it actually returns similarity directly
                score = (
                    float(hit.score)
                    if hasattr(hit, "score")
                    else float(1.0 - hit.distance)
                )
                if anchor:
                    output.append((anchor, score))

        return output

    def configure(
        self,
        *,
        top_k: Optional[int] = None,
        ef_search: Optional[int] = None,
    ) -> None:
        """Update search parameters."""
        if top_k is not None:
            self._top_k = int(top_k)
        if ef_search is not None:
            self._ef_search = int(ef_search)

    def _normalize(self, vec: np.ndarray) -> np.ndarray:
        """Normalize vector to unit length."""
        from somabrain.math import normalize_vector

        arr = np.asarray(vec, dtype=np.float32).reshape(-1)
        if arr.shape[0] != self._dim:
            raise ValueError(
                f"Vector dimension mismatch: expected {self._dim}, got {arr.shape[0]}"
            )
        return normalize_vector(arr, dtype=np.float32)

    def stats(self) -> Dict[str, object]:
        """Return index statistics."""
        return {
            "backend": "milvus",
            "collection": self._collection_name,
            "dim": self._dim,
            "tenant_id": self._tenant_id,
            "namespace": self._namespace,
            "anchor_count": len(self._anchor_to_id),
            "top_k": self._top_k,
            "ef_search": self._ef_search,
        }


def create_milvus_cleanup_index(
    dim: int,
    *,
    tenant_id: str = "default",
    namespace: str = "cleanup",
    top_k: int = 64,
    ef_search: int = 128,
) -> CleanupIndex:
    """Factory function to create a Milvus-backed CleanupIndex.

    Fails fast if Milvus is unavailable; no fallbacks permitted.
    """
    return MilvusAnnIndex(
        dim,
        tenant_id=tenant_id,
        namespace=namespace,
        top_k=top_k,
        ef_search=ef_search,
    )


__all__ = [
    "MilvusAnnIndex",
    "create_milvus_cleanup_index",
]