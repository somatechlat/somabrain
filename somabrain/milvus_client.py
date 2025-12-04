"""Thin wrapper around the official Milvus SDK.

The VIBE rules require:
* **Single source of truth** – all connection parameters come from
  ``common.config.settings``.
* **No magic numbers** – defaults are defined in ``Settings`` and referenced
  via ``settings``.
* **Typed public API** – the class exposes three methods with full type hints.

The wrapper is deliberately small: it handles connection, collection creation,
up‑sert of an option payload, and similarity search used by the Oak option
manager.  All heavy‑lifting (index creation, vector conversion) lives inside the
class so callers stay simple.
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import List, Tuple

from common.config.settings import settings
from somabrain.metrics import (
    MILVUS_INGEST_LAT_P95,
    MILVUS_SEARCH_LAT_P95,
    MILVUS_SEGMENT_LOAD,
)

# ``pymilvus`` is an optional heavy dependency. Import it lazily and provide
# fall‑backs for the test environment where the library is not installed.
# ``pymilvus`` is an optional heavy dependency. Import it lazily and provide
# fall‑backs for the test environment where the library is not installed.
try:
    from pymilvus import (
        Collection,
        connections,
        utility,
        FieldSchema,
        CollectionSchema,
        DataType,
    )
    from pymilvus.exceptions import MilvusException

    _PYMILVUS_AVAILABLE = True
except Exception:  # pragma: no cover – exercised only when pymilvus missing
    _PYMILVUS_AVAILABLE = False

    # Fallback types when pymilvus is not installed. These allow the module
    # to be imported without the optional dependency. Operations requiring
    # Milvus will fail at runtime with clear error messages.
    class _FallbackCollection:
        def __init__(self, *_, **__):
            """Fallback collection - pymilvus not available."""

    Collection = _FallbackCollection
    connections = type("_Conn", (), {"connect": staticmethod(lambda *_, **__: None)})()
    utility = type("_Util", (), {"has_collection": staticmethod(lambda *_: False)})()
    FieldSchema = object
    CollectionSchema = object
    DataType = type("_DT", (), {"VARCHAR": None, "FLOAT_VECTOR": None})
    MilvusException = Exception

logger = logging.getLogger(__name__)


def _vector_from_payload(payload: bytes, dim: int = 128) -> List[float]:
    """Deterministic float vector derived from a binary payload.

    The function hashes the payload with SHA‑256, slices the digest into 4‑byte
    chunks, converts each chunk into a float in ``[0, 1)`` and pads/truncates to
    ``dim``.  This mirrors the original deterministic vector generation used in
    the Redis implementation, ensuring functional parity.
    """
    digest = hashlib.sha256(payload).digest()
    floats: List[float] = []
    for i in range(0, len(digest), 4):
        chunk = int.from_bytes(digest[i : i + 4], "big", signed=False)
        floats.append(chunk / 2**32)
        if len(floats) >= dim:
            break
    if len(floats) < dim:
        floats.extend([0.0] * (dim - len(floats)))
    return floats


class MilvusClient:
    """Convenient wrapper for Milvus used by the Oak option subsystem.

    *All* configuration values are read from the global ``settings`` instance –
    this satisfies the VIBE “single source of truth” rule.
    """

    # Collection instance - set during __init__ when Milvus is available.
    # May be None if Milvus connection fails.
    collection: "Collection" = None

    def __init__(self) -> None:
        # Resolve host/port from Settings; ``milvus_url`` is a convenience that
        # already concatenates host and port.
        host = settings.milvus_host or "localhost"
        port = settings.milvus_port or 19530
        self.dim: int = getattr(settings, "milvus_dim", 128)  # allow override
        self.collection_name: str = settings.milvus_collection

        # Attempt to establish a connection to Milvus. Connection failures are
        # handled gracefully by logging a warning and proceeding with a None
        # collection. Operations requiring Milvus will fail with clear errors.
        try:
            connections.connect("default", host=host, port=port)
            logger.debug("Connected to Milvus at %s:%s", host, port)

            if not utility.has_collection(self.collection_name):
                # Only attempt to create the collection when the real Milvus
                # SDK is present. In the test environment ``_PYMILVUS_AVAILABLE``
                # is ``False`` and the fallback ``FieldSchema`` etc. are not
                # callable, so we skip the creation step to avoid a
                # ``TypeError`` that would be caught as a generic MilvusException
                # and prevent the ``Collection`` constructor from being invoked.
                if _PYMILVUS_AVAILABLE:
                    self._create_collection()
            # Instantiate the collection.
            self.collection: Collection = Collection(self.collection_name)
        except MilvusException as exc:
            logger.warning(
                "Milvus connection failed (%s); collection operations unavailable", exc
            )
            # Using None indicates Milvus is unavailable.
            self.collection = None

    # ---------------------------------------------------------------------
    # Private helpers
    # ---------------------------------------------------------------------
    def _create_collection(self) -> None:
        fields = [
            FieldSchema(
                name="option_id",
                dtype=DataType.VARCHAR,
                max_length=256,
                is_primary=True,
            ),
            FieldSchema(name="tenant_id", dtype=DataType.VARCHAR, max_length=256),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.dim),
        ]
        schema = CollectionSchema(fields, description="Oak option vectors")
        coll = Collection(self.collection_name, schema)
        # Use a binary IVF index suitable for Hamming distance.
        coll.create_index(
            field_name="embedding",
            index_params={
                "index_type": "BIN_IVF_FLAT",
                "metric_type": "HAMMING",
                "params": {"nlist": 128},
            },
        )
        coll.load()
        logger.info("Created Milvus collection %s", self.collection_name)

    # ---------------------------------------------------------------------
    # Public API used by Oak option manager and FastAPI routes
    # ---------------------------------------------------------------------
    def upsert_option(self, tenant_id: str, option_id: str, payload: bytes) -> None:
        """Insert or replace an option record for a tenant.

        Milvus has no native UPSERT, but inserting a row with an existing primary
        key overwrites the previous entry (the SDK performs a replace under the
        hood).  The vector is derived deterministically from ``payload``.

        This implementation now *mandates* a successful write to Milvus. If the
        Milvus collection is unavailable the operation will be retried (with
        exponential back‑off) a configurable number of times before raising an
        exception.  Failures are recorded via a dedicated counter metric so that
        operators can be alerted.
        """
        if self.collection is None:
            # Milvus client could not be initialised – treat as fatal.
            raise RuntimeError("Milvus collection is unavailable – cannot upsert option")

        # Configuration for retry behaviour – defaults are safe for production.
        max_retries: int = getattr(settings, "milvus_upsert_retries", 3)
        backoff_base: float = getattr(settings, "milvus_upsert_backoff_base", 0.5)

        attempt = 0
        while True:
            attempt += 1
            start = time.perf_counter()
            try:
                vector = _vector_from_payload(payload, dim=self.dim)
                entities = [[option_id], [tenant_id], [vector]]
                self.collection.insert(entities)
                self.collection.flush()
                elapsed = max(0.0, time.perf_counter() - start)
                # Record ingestion latency (p95 gauge) per tenant.
                MILVUS_INGEST_LAT_P95.labels(tenant_id=tenant_id).set(elapsed)
                # Update segment load – use number of entities as a proxy.
                try:
                    count = getattr(self.collection, "num_entities", None)
                    if count is not None:
                        MILVUS_SEGMENT_LOAD.labels(tenant_id=tenant_id).set(int(count))
                except Exception:
                    pass
                logger.debug(
                    "Upserted option %s for tenant %s (latency=%.4fs, attempt=%d)",
                    option_id,
                    tenant_id,
                    elapsed,
                    attempt,
                )
                # Success – exit the retry loop.
                return
            except Exception as exc:
                # Record a failure metric for visibility.
                try:
                    from somabrain.metrics import Counter as _Counter
                    # Dynamic counter name to avoid polluting existing metric set.
                    failure_counter_name = "somabrain_milvus_upsert_failure_total"
                    failure_counter = _Counter(
                        failure_counter_name,
                        "Count of Milvus upsert failures",
                        ["tenant_id"],
                    )
                    failure_counter.labels(tenant_id=tenant_id).inc()
                except Exception:
                    pass
                logger.error(
                    "Milvus upsert attempt %d failed for tenant %s, option %s: %s",
                    attempt,
                    tenant_id,
                    option_id,
                    exc,
                )
                if attempt >= max_retries:
                    # Exhausted retries – propagate the error.
                    raise
                # Exponential back‑off before the next attempt.
                sleep_time = backoff_base * (2 ** (attempt - 1))
                time.sleep(sleep_time)

    def search_similar(
        self,
        tenant_id: str,
        payload: bytes,
        top_k: int | None = None,
        similarity_threshold: float | None = None,
    ) -> List[Tuple[str, float]]:
        """Return a list of ``(option_id, similarity)`` tuples.

        The defaults are sourced from ``common.config.settings`` to avoid magic
        numbers, satisfying the VIBE *no magic numbers* rule. ``top_k`` falls back
        to ``settings.OAK_PLAN_MAX_OPTIONS`` and ``similarity_threshold`` to
        ``settings.OAK_SIMILARITY_THRESHOLD``.
        """
        # Resolve defaults from Settings if not provided.
        top_k = (
            top_k
            if top_k is not None
            else getattr(settings, "OAK_PLAN_MAX_OPTIONS", 10)
        )
        similarity_threshold = (
            similarity_threshold
            if similarity_threshold is not None
            else getattr(settings, "OAK_SIMILARITY_THRESHOLD", 0.85)
        )

        start = time.perf_counter()
        vector = _vector_from_payload(payload, dim=self.dim)
        search_params = {"metric_type": "HAMMING", "params": {"nprobe": 10}}
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
            sim = 1.0 / (1.0 + hit.distance)
            if sim >= similarity_threshold:
                out.append((hit.entity.get("option_id"), sim))
        # Record search latency metric.
        elapsed = max(0.0, time.perf_counter() - start)
        MILVUS_SEARCH_LAT_P95.labels(tenant_id=tenant_id).set(elapsed)
        return out


# End of file – only the first MilvusClient implementation remains.
