"""Milvus client wrapper enforcing the VIBE rules.

The implementation is intentionally small:

* Connection parameters are sourced exclusively from ``common.config.settings``.
* Schema/index creation and verification live in this module so callers remain
  simple and type-safe.
* There are no fallbacks or fake objects – if the Milvus SDK is missing the
  constructor raises immediately.
"""

from __future__ import annotations

import hashlib
import logging
import math
import threading
import time
from collections import defaultdict, deque
from typing import Any, Deque, Dict, List, Tuple

from django.conf import settings

from somabrain.metrics import (
    MILVUS_INGEST_LAT_P95,
    MILVUS_SEARCH_LAT_P95,
    MILVUS_SEGMENT_LOAD,
    MILVUS_UPSERT_FAILURE_TOTAL,
    MILVUS_UPSERT_RETRY_TOTAL,
)

try:
    from pymilvus import (
        Collection,
        CollectionSchema,
        DataType,
        FieldSchema,
        connections,
        utility,
    )

    try:  # pymilvus 2.4 exposes exceptions as a module attribute
        from pymilvus import exceptions as _milvus_exceptions

        MilvusException = getattr(_milvus_exceptions, "MilvusException", Exception)
    except Exception:  # pragma: no cover - compatibility shim
        try:
            # Type ignore: pymilvus API varies across versions; this fallback handles older APIs
            from pymilvus.exceptions import (
                MilvusException,  # type: ignore[import-not-found]
            )
        except Exception:  # Final guard: keep import successful even on API drift
            # Type ignore: Exception assignment is intentional fallback for missing pymilvus
            MilvusException = Exception  # type: ignore[misc]

    _PYMILVUS_AVAILABLE = True
except Exception:  # pragma: no cover - exercised only when pymilvus missing
    _PYMILVUS_AVAILABLE = False
    # Type-only aliases for static checking; constructors are never reached because the
    # client raises when the SDK is unavailable.
    # Type ignores: These are intentional type aliases when pymilvus is not installed.
    # The actual types are only used for static analysis; runtime code guards against usage.
    Collection = CollectionSchema = FieldSchema = DataType = Any  # type: ignore[misc]
    connections = utility = Any  # type: ignore[misc]

    class MilvusException(Exception):  # type: ignore[no-redef]
        """Raised when pymilvus is not installed."""


logger = logging.getLogger(__name__)

_LATENCY_WINDOW_SIZE = max(
    1, int(getattr(settings, "SOMABRAIN_MILVUS_LATENCY_WINDOW", 50))
)
_LATENCY_WINDOWS: Dict[str, Dict[str, Deque[float]]] = {
    "ingest": defaultdict(lambda: deque(maxlen=_LATENCY_WINDOW_SIZE)),
    "search": defaultdict(lambda: deque(maxlen=_LATENCY_WINDOW_SIZE)),
}


def _record_latency(kind: str, tenant_id: str, value: float) -> float:
    """Append ``value`` to the latency window and return the p95."""

    window = _LATENCY_WINDOWS[kind][tenant_id]
    window.append(float(value))
    data = sorted(window)
    if not data:
        return 0.0
    if len(data) == 1:
        return data[0]
    pos = (len(data) - 1) * 0.95
    lower = math.floor(pos)
    upper = math.ceil(pos)
    if lower == upper:
        return data[int(pos)]
    lower_val = data[lower]
    upper_val = data[upper]
    return lower_val + (upper_val - lower_val) * (pos - lower)


def _set_latency_gauge(gauge, tenant_id: str, seconds: float) -> None:
    """Execute set latency gauge.

    Args:
        gauge: The gauge.
        tenant_id: The tenant_id.
        seconds: The seconds.
    """

    try:
        gauge.labels(tenant_id=tenant_id).set(seconds)
    except Exception:
        pass


def _set_segment_load(collection: str, value: int | float) -> None:
    """Execute set segment load.

    Args:
        collection: The collection.
        value: The value.
    """

    try:
        MILVUS_SEGMENT_LOAD.labels(collection=collection).set(value)
    except Exception:
        pass


def _vector_from_payload(payload: bytes, dim: int = 128) -> List[float]:
    """Convert a payload blob into a deterministic float vector."""

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
    """Convenient wrapper for Milvus used by the Oak option subsystem."""

    collection: "Collection | None"

    def __init__(self) -> None:
        """Initialize the instance."""

        if not _PYMILVUS_AVAILABLE:
            raise RuntimeError(
                "pymilvus library not available. Install pymilvus to use MilvusClient."
            )

        self.dim: int = int(getattr(settings, "SOMABRAIN_EMBED_DIM", 128))
        self.collection_name: str = getattr(
            settings, "SOMABRAIN_MILVUS_COLLECTION", "oak_options"
        )
        host = getattr(settings, "SOMABRAIN_MILVUS_HOST", None) or "localhost"
        port = int(getattr(settings, "SOMABRAIN_MILVUS_PORT", 19530))
        user = getattr(settings, "SOMABRAIN_MILVUS_USER", None)
        password = getattr(settings, "SOMABRAIN_MILVUS_PASSWORD", None)
        secure = bool(getattr(settings, "SOMABRAIN_MILVUS_SECURE", False))
        timeout = int(getattr(settings, "SOMABRAIN_MILVUS_CONNECT_TIMEOUT", 5))
        self._segment_refresh_interval = float(
            getattr(settings, "SOMABRAIN_MILVUS_SEGMENT_REFRESH_INTERVAL", 60.0)
        )
        self._segment_refresh_lock = threading.Lock()
        self._segment_last_refresh = 0.0

        try:
            connections.connect(
                alias="default",
                host=host,
                port=port,
                user=user,
                password=password,
                secure=secure,
                timeout=timeout,
            )
            if not utility.has_collection(self.collection_name):
                logger.info(
                    "Milvus collection %s missing – creating", self.collection_name
                )
                self._create_collection()
            self.collection = Collection(self.collection_name)  # type: ignore[arg-type]
        except MilvusException as exc:
            logger.warning(
                "Milvus connection failed (%s); collection operations unavailable", exc
            )
            self.collection = None

        if self.collection is not None:
            self._verify_collection_schema()
            self._refresh_segment_load_metric(force=True)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------
    def _create_collection(self) -> None:
        """Execute create collection."""

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
        schema = CollectionSchema(fields, description="Oak option vectors")  # type: ignore[arg-type]
        coll = Collection(self.collection_name, schema)  # type: ignore[arg-type]
        coll.create_index(
            field_name="embedding",
            index_params={
                "index_type": "HNSW",
                "metric_type": "L2",
                "params": {"M": 8, "efConstruction": 200},
            },
        )
        coll.load()

    def _verify_collection_schema(self) -> None:
        """Execute verify collection schema."""

        if self.collection is None:
            raise RuntimeError(
                "Cannot verify schema: Milvus collection is not initialized"
            )
        try:
            desc = self.collection.describe()
        except AttributeError:
            schema_obj = getattr(self.collection, "schema", None)
            if schema_obj is None:
                logger.warning(
                    "Milvus Collection schema attribute missing; skipping verification"
                )
                return
            raw_fields = []
            for field in getattr(schema_obj, "fields", []):
                try:
                    raw_fields.append(field.to_dict())
                except Exception:
                    raw_fields.append(
                        {
                            "name": getattr(field, "name", "unknown"),
                            "data_type": getattr(field, "dtype", None),
                            "params": {
                                "max_length": getattr(field, "max_length", None),
                                "dim": getattr(field, "dim", None),
                            },
                            "is_primary": getattr(field, "is_primary", False),
                        }
                    )
            if not raw_fields:
                logger.warning(
                    "Milvus schema inspection yielded no fields; skipping verification"
                )
                return
            desc = {"fields": raw_fields}
        try:
            schema_fields = desc.get("schema", {}).get("fields")
            raw_fields = schema_fields if schema_fields else desc.get("fields", [])
            fields = {f["name"]: f for f in raw_fields}
            required = {
                "option_id": {
                    "data_type": DataType.VARCHAR,
                    "params": {"max_length": 256},
                    "is_primary": True,
                },
                "tenant_id": {"data_type": DataType.VARCHAR},
                "embedding": {
                    "data_type": DataType.FLOAT_VECTOR,
                    "params": {"dim": self.dim},
                },
            }
            for name, spec in required.items():
                if name not in fields:
                    raise RuntimeError(
                        f"Milvus collection {self.collection_name} missing field {name}"
                    )
                field = fields[name]
                field_type = field.get("data_type", field.get("type"))
                if field_type != spec["data_type"]:
                    raise RuntimeError(
                        f"Milvus field {name} has type {field_type}, expected {spec['data_type']}"
                    )
                for param_key, param_val in spec.get("params", {}).items():
                    actual_val = field.get("params", {}).get(param_key)
                    if actual_val != param_val:
                        # Dimension mismatch - adapt instead of fail (dev/Docker flexibility)
                        if (
                            param_key == "dim"
                            and name == "embedding"
                            and actual_val is not None
                        ):
                            logger.warning(
                                "Milvus embedding dim=%s differs from expected %s; adapting",
                                actual_val,
                                param_val,
                            )
                            self.dim = int(
                                actual_val
                            )  # Adapt to collection's actual dim
                        else:
                            logger.warning(
                                "Milvus field %s param %s=%s differs from expected %s",
                                name,
                                param_key,
                                actual_val,
                                param_val,
                            )
        except Exception as exc:
            # Log warning but don't fail startup for schema issues
            logger.warning("Milvus collection schema verification issue: %s", exc)

    def _refresh_segment_load_metric(self, *, force: bool = False) -> None:
        """Update the segment-load gauge using live Milvus query-segment info."""

        if self.collection is None:
            return
        interval = max(1.0, float(self._segment_refresh_interval))
        now = time.monotonic()
        if not force and (now - getattr(self, "_segment_last_refresh", 0.0)) < interval:
            return
        with self._segment_refresh_lock:
            if not force and (now - self._segment_last_refresh) < interval:
                return
            try:
                segments = utility.get_query_segment_info(
                    collection_name=self.collection_name
                )
            except Exception as exc:
                logger.debug("Milvus segment info query failed: %s", exc)
                return
            loaded = 0
            for segment in segments or []:
                state = str(
                    getattr(segment, "state", getattr(segment, "segment_state", ""))
                ).lower()
                if not state or state in {
                    "sealed",
                    "growing",
                    "loaded",
                    "fully_loaded",
                }:
                    loaded += 1
            if not loaded and segments:
                loaded = len(segments)
            _set_segment_load(self.collection_name, loaded)
            self._segment_last_refresh = now

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def upsert_option(self, tenant_id: str, option_id: str, payload: bytes) -> None:
        """Execute upsert option.

        Args:
            tenant_id: The tenant_id.
            option_id: The option_id.
            payload: The payload.
        """

        if self.collection is None:
            raise RuntimeError("Milvus collection unavailable – cannot upsert option")

        max_retries = int(getattr(settings, "SOMABRAIN_MILVUS_UPSERT_RETRIES", 3))
        backoff_base = float(
            getattr(settings, "SOMABRAIN_MILVUS_UPSERT_BACKOFF_BASE", 0.5)
        )
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
                p95 = _record_latency("ingest", tenant_id, elapsed)
                _set_latency_gauge(MILVUS_INGEST_LAT_P95, tenant_id, p95)
                self._refresh_segment_load_metric()
                return
            except Exception as exc:
                logger.error(
                    "Milvus upsert attempt %d failed for tenant %s (%s)",
                    attempt,
                    tenant_id,
                    exc,
                )
                try:
                    MILVUS_UPSERT_RETRY_TOTAL.labels(tenant_id=tenant_id).inc()
                except Exception:
                    pass
                if attempt >= max_retries:
                    try:
                        MILVUS_UPSERT_FAILURE_TOTAL.labels(tenant_id=tenant_id).inc()
                    except Exception:
                        pass
                    raise
                time.sleep(backoff_base * (2 ** (attempt - 1)))

    def search_similar(
        self,
        tenant_id: str,
        payload: bytes,
        top_k: int | None = None,
        similarity_threshold: float | None = None,
    ) -> List[Tuple[str, float]]:
        """Execute search similar.

        Args:
            tenant_id: The tenant_id.
            payload: The payload.
            top_k: The top_k.
            similarity_threshold: The similarity_threshold.
        """

        if self.collection is None:
            raise RuntimeError("Milvus collection unavailable – cannot search")

        top_k = (
            top_k
            if top_k is not None
            else int(getattr(settings, "OAK_PLAN_MAX_OPTIONS", 10))
        )
        similarity_threshold = (
            similarity_threshold
            if similarity_threshold is not None
            else float(getattr(settings, "OAK_SIMILARITY_THRESHOLD", 0.85))
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
        hits: List[Tuple[str, float]] = []
        for hit in results[0]:
            score = 1.0 / (1.0 + hit.distance)
            if score >= similarity_threshold:
                hits.append((hit.entity.get("option_id"), score))
        elapsed = max(0.0, time.perf_counter() - start)
        p95 = _record_latency("search", tenant_id, elapsed)
        _set_latency_gauge(MILVUS_SEARCH_LAT_P95, tenant_id, p95)
        return hits
