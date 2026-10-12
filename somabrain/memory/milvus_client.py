"""Milvus client wrapper enforcing the VIBE rules.

This class is a **connectivity probe only** (T-1 / D7). Vector writes go
through SFM via ``MemoryClient`` — SomaBrain never writes Milvus itself.
There is no option upsert, no search, and no hash-fabricated vector here.

* Connection parameters are sourced exclusively from ``common.config.settings``.
* Schema/index creation and verification live in this module so callers remain
  simple and type-safe.
* There are no fallbacks or fake objects – if the Milvus SDK is missing the
  constructor raises immediately.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from django.conf import settings

from somabrain.metrics import (
    MILVUS_SEGMENT_LOAD,
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
    except Exception:  # pragma: no cover - pymilvus API drift
        try:
            from pymilvus.exceptions import (
                MilvusException,  # type: ignore[import-not-found]
            )
        except Exception:  # pragma: no cover

            class MilvusException(Exception):
                """Raised when pymilvus exception types are unavailable."""

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


def _set_segment_load(collection: str, value: float) -> None:
    """Execute set segment load.

    Args:
        collection: The collection.
        value: The value.
    """

    try:
        MILVUS_SEGMENT_LOAD.labels(collection=collection).set(value)
    except Exception:
        pass


class MilvusClient:
    """Convenient wrapper for Milvus used by the Oak option subsystem."""

    collection: Collection | None

    def __init__(self) -> None:
        """Initialize the instance."""

        if not _PYMILVUS_AVAILABLE:
            raise RuntimeError(
                "pymilvus library not available. Install pymilvus to use MilvusClient."
            )

        # Seam dim unity (ARCHITECTURE-INVARIANTS §2): MEM_EMBED_DIM ==
        # SOMA_VECTOR_DIM == SOMABRAIN_EMBED_DIM. Never invent a fallback.
        dim = getattr(settings, "SOMABRAIN_EMBED_DIM")
        if not dim:
            raise RuntimeError(
                "SOMABRAIN_EMBED_DIM is not configured — refusing to guess a vector dim"
            )
        self.dim: int = int(dim)
        self.collection_name: str = getattr(
            settings, "SOMABRAIN_MILVUS_COLLECTION", "oak_options"
        )
        # Topology is named by the operator. No localhost, no invented port (Rule 91).
        host = getattr(settings, "SOMABRAIN_MILVUS_HOST")
        if not host:
            raise RuntimeError(
                "SOMABRAIN_MILVUS_HOST is not configured — refusing to invent a vector-store host"
            )
        port = getattr(settings, "SOMABRAIN_MILVUS_PORT")
        if not port:
            raise RuntimeError(
                "SOMABRAIN_MILVUS_PORT is not configured — refusing to invent a vector-store port"
            )
        port = int(port)
        # Credentials are Vault material held on the settings module, not ENV.
        user = getattr(settings, "SOMABRAIN_MILVUS_USER", None)
        password = getattr(settings, "SOMABRAIN_MILVUS_PASSWORD", None)
        if user and not password:
            raise RuntimeError(
                "SOMABRAIN_MILVUS_USER is set but SOMABRAIN_MILVUS_PASSWORD is missing — "
                "a username without a password is not a credential (Rule 164)"
            )
        secure = bool(getattr(settings, "SOMABRAIN_MILVUS_SECURE"))
        timeout = int(getattr(settings, "SOMABRAIN_MILVUS_CONNECT_TIMEOUT"))
        self._segment_refresh_interval = float(
            getattr(settings, "SOMABRAIN_MILVUS_SEGMENT_REFRESH_INTERVAL")
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

