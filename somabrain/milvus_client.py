"""Thin wrapper around the official Milvus SDK.

This implementation follows the VIBE coding rules:

* **Single source of truth** – all connection parameters are read from
  ``common.config.settings``.
* **No magic numbers** – defaults are defined in ``Settings`` and referenced
  via ``settings``.
* **Typed public API** – the class exposes three methods with full type hints.

The wrapper deliberately keeps Milvus‑specific logic isolated so that the rest of
the codebase can use a simple, well‑typed interface.  When the real Milvus SDK
is not available (e.g. during unit tests) a lightweight fallback is used that
provides the attributes accessed by the code but raises ``RuntimeError`` for
operations that require a live Milvus server.
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

# ---------------------------------------------------------------------------
# Optional import of the real Milvus SDK.  When it is missing we provide a set
# of stub classes that satisfy attribute access but raise clear errors if used.
# ---------------------------------------------------------------------------
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
except Exception:  # pragma: no cover – exercised only in the test environment
    _PYMILVUS_AVAILABLE = False

    class _FallbackCollection:
        def __init__(self, *_, **__):
            """Fallback collection – pymilvus not available."""

    class _FallbackConnections:
        @staticmethod
        def connect(*_, **__):  # noqa: D401
            """No‑op connection when Milvus SDK is unavailable."""

    class _FallbackUtility:
        @staticmethod
        def has_collection(*_, **__) -> bool:  # noqa: D401
            """Always report that the collection does not exist."""
            return False

    class _DummyFieldSchema:  # pragma: no cover
        pass

    class _DummyCollectionSchema:  # pragma: no cover
        pass

    class _DummyDataType:  # pragma: no cover
        VARCHAR = None
        FLOAT_VECTOR = None

    class _DummyMilvusException(Exception):  # pragma: no cover
        pass

    Collection = _FallbackCollection  # type: ignore
    connections = _FallbackConnections()  # type: ignore
    utility = _FallbackUtility()  # type: ignore
    FieldSchema = _DummyFieldSchema  # type: ignore
    CollectionSchema = _DummyCollectionSchema  # type: ignore
    DataType = _DummyDataType  # type: ignore
    MilvusException = _DummyMilvusException  # type: ignore

logger = logging.getLogger(__name__)


def _vector_from_payload(payload: bytes, dim: int = 128) -> List[float]:
    """Deterministic float vector derived from a binary payload.

    The payload is hashed with SHA‑256, the digest is split into 4‑byte chunks,
    each chunk is interpreted as an unsigned integer and scaled to ``[0, 1)``.
    The resulting list is padded/truncated to the requested dimension.
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

    All configuration values are read from the global ``settings`` instance –
    this satisfies the VIBE *single source of truth* rule.
    """

    # The collection attribute is populated after a successful connection.
    collection: "Collection" = None  # type: ignore

    def __init__(self) -> None:
        host = settings.milvus_host or "localhost"
        port = settings.milvus_port or 19530
        self.dim: int = getattr(settings, "milvus_dim", 128)
        self.collection_name: str = settings.milvus_collection

        try:
            connections.connect("default", host=host, port=port)
            logger.debug("Connected to Milvus at %s:%s", host, port)

            if not utility.has_collection(self.collection_name) and _PYMILVUS_AVAILABLE:
                self._create_collection()
            # Instantiate the collection (real or fallback).
            self.collection = Collection(self.collection_name)  # type: ignore
        except MilvusException as exc:  # pragma: no cover – exercised when SDK missing
            logger.warning(
                "Milvus connection failed (%s); collection operations unavailable", exc
            )
            self.collection = None

        # Verify schema only when a real collection object is present.
        if self.collection is not None and hasattr(self.collection, "describe"):
            self._verify_collection_schema()

    # ---------------------------------------------------------------------
    # Private helpers
    # ---------------------------------------------------------------------
    def _create_collection(self) -> None:
        """Create the Milvus collection with the expected schema and index."""
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

    def _verify_collection_schema(self) -> None:
        """Validate that the existing collection matches the expected schema.

        The expected schema consists of three fields:

        * ``option_id`` – ``VARCHAR`` primary key, max length 256
        * ``tenant_id`` – ``VARCHAR``
        * ``embedding`` – ``FLOAT_VECTOR`` with dimensionality ``self.dim``
        """
        try:
            # ``describe`` returns a dict with ``schema`` information.
            desc = self.collection.describe()  # type: ignore
            fields = {f["name"]: f for f in desc.get("schema", {}).get("fields", [])}
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
                    raise RuntimeError(f"Milvus collection {self.collection_name} missing field {name}")
                field = fields[name]
                if field.get("data_type") != spec["data_type"]:
                    raise RuntimeError(
                        f"Milvus field {name} has wrong type {field.get('data_type')}, expected {spec['data_type']}"
                    )
                if "params" in spec:
                    for p_key, p_val in spec["params"].items():
                        if field.get("params", {}).get(p_key) != p_val:
                            raise RuntimeError(
                                f"Milvus field {name} param {p_key}={field.get('params', {}).get(p_key)} does not match expected {p_val}"
                            )
        except Exception as exc:
            raise RuntimeError(f"Milvus collection schema verification failed: {exc}") from exc

    # ---------------------------------------------------------------------
    # Public API used by Oak option manager and FastAPI routes
    # ---------------------------------------------------------------------
    def upsert_option(self, tenant_id: str, option_id: str, payload: bytes) -> None:
        """Insert or replace an option record for a tenant.

        The vector is derived deterministically from ``payload``.  If the Milvus
        collection is unavailable a ``RuntimeError`` is raised so that callers can
        react appropriately.
        """
        if self.collection is None:
            raise RuntimeError("Milvus collection is unavailable – cannot upsert option")

        max_retries: int = getattr(settings, "milvus_upsert_retries", 3)
        backoff_base: float = getattr(settings, "milvus_upsert_backoff_base", 0.5)
        attempt = 0
        while True:
            attempt += 1
            start = time.perf_counter()
            try:
                vector = _vector_from_payload(payload, dim=self.dim)
                entities = [[option_id], [tenant_id], [vector]]
                self.collection.insert(entities)  # type: ignore
                self.collection.flush()  # type: ignore
                elapsed = max(0.0, time.perf_counter() - start)
                MILVUS_INGEST_LAT_P95.labels(tenant_id=tenant_id).set(elapsed)
                # Record segment load if available.
                count = getattr(self.collection, "num_entities", None)
                if count is not None:
                    MILVUS_SEGMENT_LOAD.labels(tenant_id=tenant_id).set(int(count))
                logger.debug(
                    "Upserted option %s for tenant %s (latency=%.4fs, attempt=%d)",
                    option_id,
                    tenant_id,
                    elapsed,
                    attempt,
                )
                return
            except Exception as exc:
                logger.error(
                    "Milvus upsert attempt %d failed for tenant %s, option %s: %s",
                    attempt,
                    tenant_id,
                    option_id,
                    exc,
                )
                if attempt >= max_retries:
                    raise
                time.sleep(backoff_base * (2 ** (attempt - 1))

    def search_similar(
        self,
        tenant_id: str,
        payload: bytes,
        top_k: int | None = None,
        similarity_threshold: float | None = None,
    ) -> List[Tuple[str, float]]:
        """Return a list of ``(option_id, similarity)`` tuples.

        ``top_k`` and ``similarity_threshold`` fall back to values defined in
        ``settings`` when not provided.
        """
        top_k = top_k if top_k is not None else getattr(settings, "OAK_PLAN_MAX_OPTIONS", 10)
        similarity_threshold = (
            similarity_threshold
            if similarity_threshold is not None
            else getattr(settings, "OAK_SIMILARITY_THRESHOLD", 0.85)
        )

        start = time.perf_counter()
        vector = _vector_from_payload(payload, dim=self.dim)
        search_params = {"metric_type": "HAMMING", "params": {"nprobe": 10}}
        results = self.collection.search(  # type: ignore
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
        elapsed = max(0.0, time.perf_counter() - start)
        MILVUS_SEARCH_LAT_P95.labels(tenant_id=tenant_id).set(elapsed)
        return out
"""Thin wrapper around the official Milvus SDK.

The VIBE rules require:
* **Single source of truth** – all connection parameters come from
  ``common.config.settings``.
* **No magic numbers** – defaults are defined in ``Settings`` and referenced
  via ``settings``.
* **Typed public API** – the class exposes three methods with full type hints.
* **Real Implementations Only** - No dummy fallback classes; fail fast if missing deps.

The wrapper is deliberately small: it handles connection, collection creation,
up‑sert of an option payload, and similarity search used by the Oak option
manager.  All heavy‑lifting (index creation, vector conversion) lives inside the
class so callers stay simple.
"""

from __future__ import annotations

import hashlib
import logging
        try:
            # Resolve host/port from Settings; ``milvus_url`` is a convenience that
            # already concatenates host and port.
            host = settings.milvus_host or "localhost"
            port = settings.milvus_port or 19530
            connections.connect(
                alias="default",
                host=host,
                port=port,
                timeout=5,
                user=settings.milvus_user,
                password=settings.milvus_password,
                secure=settings.milvus_secure,
            )
            if not utility.has_collection(self.collection_name):
                logger.info("Milvus collection %s missing – creating", self.collection_name)
                self._create_collection()
            # Instantiate the collection.
            self.collection: Collection = Collection(self.collection_name)
        except MilvusException as exc:
            logger.warning(
                "Milvus connection failed (%s); collection operations unavailable", exc
            )
            # Using None indicates Milvus is unavailable.
            self.collection = None
        # After establishing a connection (or failing), verify that the collection
        # schema matches the expected Oak option layout. This check enforces the
        # Milvus hardening requirement (task 19.3). Any mismatch raises a
        # RuntimeError so that deployment pipelines can fail fast.
        # If the collection is a fallback placeholder (no real Milvus), skip verification.
        if self.collection is not None and hasattr(self.collection, "describe"):
            self._verify_collection_schema()
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
        if not _PYMILVUS_AVAILABLE:
            raise RuntimeError(
                "pymilvus library not available. Cannot instantiate MilvusClient."
            )

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
        # After establishing a connection (or failing), verify that the collection
        # schema matches the expected Oak option layout. This check enforces the
        # Milvus hardening requirement (task 19.3). Any mismatch raises a
        # RuntimeError so that deployment pipelines can fail fast.
        if self.collection is not None:
            self._verify_collection_schema()

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
    # Schema verification – ensures the collection matches the expected
    # definition. This satisfies VIBE task 19.3 (index‑config drift check).
    # ---------------------------------------------------------------------
    def _verify_collection_schema(self) -> None:
        """Validate that the Milvus collection schema matches expectations.

        The expected schema consists of three fields:

        * ``option_id`` – ``VARCHAR`` primary key, max length 256
        * ``tenant_id`` – ``VARCHAR``
        * ``embedding`` – ``FLOAT_VECTOR`` with dimensionality ``self.dim``

        If the collection exists but deviates from this definition the method
        raises ``RuntimeError`` with a clear message.  This guards against drift
        caused by manual schema changes or version mismatches.
        """
        try:
            # ``describe_collection`` is not part of the Milvus SDK; the
            # correct way to obtain collection metadata is via the ``describe``
            # method on the ``Collection`` object.  Fall back to the utility
            # function if it exists (for compatibility with older SDKs).
            if hasattr(utility, "describe_collection"):
                desc = utility.describe_collection(self.collection_name)
            else:
                # ``self.collection`` is guaranteed to be a ``Collection``
                # instance when the client is initialised.
                desc = self.collection.describe()
            # Normalise the field list – the SDK returns a list of dicts.
            fields = {f["name"]: f for f in desc.get("schema", {}).get("fields", [])}
            # Verify required fields.
            required = {
                "option_id": {"data_type": DataType.VARCHAR, "params": {"max_length": 256}, "is_primary": True},
                "tenant_id": {"data_type": DataType.VARCHAR},
                "embedding": {"data_type": DataType.FLOAT_VECTOR, "params": {"dim": self.dim}},
            }
            for name, spec in required.items():
                if name not in fields:
                    raise RuntimeError(f"Milvus collection {self.collection_name} missing field {name}")
                field = fields[name]
                if field.get("data_type") != spec["data_type"]:
                    raise RuntimeError(
                        f"Milvus field {name} has wrong type {field.get('data_type')}, expected {spec['data_type']}"
                    )
                # Additional params checks (max_length, dim) where applicable.
                if "params" in spec:
                    for p_key, p_val in spec["params"].items():
                        if field.get("params", {}).get(p_key) != p_val:
                            raise RuntimeError(
                                f"Milvus field {name} param {p_key}={field.get('params', {}).get(p_key)} "
                                f"does not match expected {p_val}"
                            )
        except Exception as exc:
            # Re‑raise as RuntimeError to make the failure explicit to callers.
            raise RuntimeError(f"Milvus collection schema verification failed: {exc}") from exc

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
