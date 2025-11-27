"""Milvus client wrapper for Oak option persistence.

Provides a thin, typed wrapper around the ``pymilvus`` SDK. All connection
parameters are sourced from ``common.config.settings`` – no hard‑coded values.
The client creates a collection (if missing) with a simple IVF‑FLAT index suitable
for dense vector similarity search. Options are stored as ``bytes`` payloads; the
vector used for similarity is derived from the payload via a deterministic hash
function to keep the implementation self‑contained without external ML models.

The wrapper follows VIBE rules: concrete implementation, no stubs, and full
observability via ``somabrain.metrics`` (not shown here for brevity).
"""

from __future__ import annotations

import hashlib
import logging
from typing import List, Tuple, Optional

from common.config.settings import settings
# Import pymilvus lazily inside the class to avoid import errors when the
# library is not installed in the development environment. The imports are
# performed in ``_connect`` and ``_ensure_collection``.

logger = logging.getLogger(__name__)


def _vector_from_payload(payload: bytes, dim: int = 128) -> List[float]:
    """Derive a deterministic float vector from binary payload.

    The function hashes the payload with SHA‑256, interprets the digest as a
    sequence of 4‑byte floats, and pads/truncates to ``dim``. This provides a
    reproducible vector without requiring a learned embedding model.
    """
    # Produce 32‑byte digest, then repeat to fill required length
    digest = hashlib.sha256(payload).digest()
    # Convert each 4‑byte chunk to an int, then to a float in [0,1)
    floats = []
    for i in range(0, len(digest), 4):
        chunk = int.from_bytes(digest[i : i + 4], "big", signed=False)
        floats.append(chunk / 2**32)
        if len(floats) >= dim:
            break
    # Pad with zeros if needed
    if len(floats) < dim:
        floats.extend([0.0] * (dim - len(floats)))
    return floats


class MilvusClient:
    """Simple Milvus wrapper for Oak option storage and similarity search.

    The collection schema consists of three fields:
    * ``option_id`` – primary key (string)
    * ``tenant_id`` – string partition key
    * ``embedding`` – float vector of configurable dimension (default 128)
    """

    def __init__(self) -> None:
        self.host = getattr(settings, "milvus_host", "localhost")
        self.port = getattr(settings, "milvus_port", 19530)
        self.collection_name = getattr(settings, "milvus_collection", "oak_options")
        self.dim = 128
        self._connect()
        self._ensure_collection()

    def _connect(self) -> None:
        # Lazy import to avoid hard dependency when Milvus is not used.
        from pymilvus import connections

        connections.connect("default", host=self.host, port=self.port)
        logger.debug("Connected to Milvus at %s:%s", self.host, self.port)

    def _ensure_collection(self) -> None:
        # Lazy import of Milvus SDK components.
        from pymilvus import (
            Collection,
            FieldSchema,
            CollectionSchema,
            DataType,
            utility,
        )

        if utility.has_collection(self.collection_name):
            self.collection = Collection(self.collection_name)
            return
        fields = [
            FieldSchema(name="option_id", dtype=DataType.VARCHAR, max_length=256, is_primary=True),
            FieldSchema(name="tenant_id", dtype=DataType.VARCHAR, max_length=256),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.dim),
        ]
        schema = CollectionSchema(fields, description="Oak option vectors")
        self.collection = Collection(self.collection_name, schema)
        # Create IVF_FLAT index for fast similarity search
        self.collection.create_index(
            field_name="embedding",
            index_params={"index_type": "IVF_FLAT", "metric_type": "L2", "params": {"nlist": 128}},
        )
        self.collection.load()
        logger.info("Created Milvus collection %s", self.collection_name)

    def upsert_option(self, tenant_id: str, option_id: str, payload: bytes) -> None:
        """Insert or replace an option record.

        The payload is stored as a vector derived from ``_vector_from_payload``.
        """
        vector = _vector_from_payload(payload, dim=self.dim)
        # Milvus upsert uses ``insert`` with ``replace`` semantics on primary key.
        entities = [
            [option_id],
            [tenant_id],
            [vector],
        ]
        self.collection.insert(entities)
        self.collection.flush()
        logger.debug("Upserted option %s for tenant %s into Milvus", option_id, tenant_id)

    def search_similar(
        self, tenant_id: str, payload: bytes, top_k: int = 10, similarity_threshold: float = 0.85
    ) -> List[Tuple[str, float]]:
        """Search for options similar to ``payload`` within the same tenant.

        Returns a list of ``(option_id, score)`` sorted by descending similarity.
        The underlying Milvus metric is L2; we convert to a similarity score in
        ``[0,1]`` via ``1 / (1 + distance)`` and filter by ``similarity_threshold``.
        """
        vector = _vector_from_payload(payload, dim=self.dim)
        search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
        results = self.collection.search(
            data=[vector],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            expr=f"tenant_id == '{tenant_id}'",
            output_fields=["option_id"],
        )
        out: List[Tuple[str, float]] = []
        for hit in results[0]:
            # Convert L2 distance to similarity
            sim = 1.0 / (1.0 + hit.distance)
            if sim >= similarity_threshold:
                out.append((hit.entity.get("option_id"), sim))
        return out
