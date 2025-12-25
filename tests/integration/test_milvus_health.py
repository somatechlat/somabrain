from __future__ import annotations

import time
from typing import List

import numpy as np
import pytest


# Lazily import pymilvus with a marshmallow compatibility shim to avoid module-level skips.
def _milvus_import():
    try:  # pragma: no cover - shim
        import marshmallow

        ver = marshmallow.__version__.split(".")
        marshmallow.__version_info__ = tuple(int(x) for x in ver)
        marshmallow.__dict__["__version_info__"] = (
            marshmallow.__version_info__
        )  # ensure attr exists in __dict__
    except Exception:
        pass

    try:
        from pymilvus import (
            Collection,
            CollectionSchema,
            DataType,
            FieldSchema,
            connections,
            utility,
        )

        return Collection, CollectionSchema, DataType, FieldSchema, connections, utility
    except Exception as exc:
        # Fallback attempt: patch minimal marshmallow shim and retry once
        import sys
        import types

        mm = types.ModuleType("marshmallow")
        mm.__version__ = "3.26.1"
        mm.__version_info__ = (3, 26, 1)
        sys.modules["marshmallow"] = mm
        try:
            from pymilvus import (
                Collection,
                CollectionSchema,
                DataType,
                FieldSchema,
                connections,
                utility,
            )

            return (
                Collection,
                CollectionSchema,
                DataType,
                FieldSchema,
                connections,
                utility,
            )
        except Exception:
            pytest.skip(f"pymilvus not available: {exc}", allow_module_level=True)
            raise


from django.conf import settings

# Use centralized Settings for test configuration
MILVUS_HOST = settings.MILVUS_HOST or "localhost"
MILVUS_PORT = settings.MILVUS_PORT or 19530
COLL = settings.MILVUS_COLLECTION or "oak_options"


def _milvus_ready() -> bool:
    _, _, _, _, connections, utility = _milvus_import()
    for _ in range(10):
        try:
            try:
                connections.disconnect(alias="default")
            except Exception:
                pass
            connections.connect(alias="default", host=MILVUS_HOST, port=MILVUS_PORT)
            version_fn = getattr(utility, "get_server_version", None)
            if callable(version_fn):
                _ = version_fn()
            else:
                # Fallback for pymilvus 2.4+: ensure connection metadata resolves.
                connections.get_connection_addr(alias="default")
            return True
        except Exception:
            time.sleep(1.0)
    return False


def _build_temp_collection(name: str, dim: int = 4) -> Collection:
    Collection, CollectionSchema, DataType, FieldSchema, _, _ = _milvus_import()
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=False),
        FieldSchema(name="anchor_id", dtype=DataType.VARCHAR, max_length=128),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=dim),
    ]
    schema = CollectionSchema(fields, description="golden-set smoke")
    coll = Collection(name, schema)
    coll.create_index(
        field_name="vector",
        index_params={
            "index_type": "IVF_FLAT",
            "metric_type": "L2",
            "params": {"nlist": 16},
        },
    )
    coll.load()
    return coll


@pytest.mark.integration
def test_milvus_golden_recall_smoke() -> None:
    """Insert a tiny golden set and verify nearest neighbor recall@1 == 1."""
    assert _milvus_ready(), "Milvus not reachable at configured host/port"

    Collection, _, _, _, _, _ = _milvus_import()
    uniq = f"soma_golden_{int(time.time() * 1000)}"
    coll = _build_temp_collection(uniq, dim=4)

    # Three orthogonal-ish vectors
    vecs = np.asarray(
        [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
        ],
        dtype=np.float32,
    )
    ids = [0, 1, 2]
    anchors = ["a", "b", "c"]
    coll.insert([ids, anchors, vecs.tolist()])
    coll.flush()
    coll.load()
    time.sleep(0.5)

    query = [0.98, 0.01, 0.01, 0.0]
    res: List = coll.search(
        data=[query],
        anns_field="vector",
        param={"metric_type": "L2", "params": {"nprobe": 8}},
        limit=1,
        expr=None,
        output_fields=["anchor_id"],
    )[0]
    assert len(res) == 1, f"expected 1 result, got {len(res)}"
    top_anchor = res[0].entity.get("anchor_id")
    assert top_anchor == "a"

    coll.drop()


@pytest.mark.integration
def test_milvus_collection_schema_and_index() -> None:
    """Validate collection schema/index for the configured collection if it exists."""
    assert _milvus_ready(), "Milvus not reachable at configured host/port"

    Collection, _, DataType, _, _, utility = _milvus_import()

    assert utility.has_collection(COLL), f"Milvus collection '{COLL}' not found"

    coll = Collection(COLL)
    # Validate fields
    field_names = {f.name: f for f in coll.schema.fields}
    vector_field = field_names.get("vector") or field_names.get("embedding")
    assert vector_field is not None, "Missing vector field"
    assert vector_field.dtype == DataType.FLOAT_VECTOR

    # Validate index params
    idxes = coll.indexes
    if not idxes:
        pytest.skip("Milvus driver did not expose index metadata for current backend")
    idx_params = idxes[0].params
    assert idx_params.get("index_type") in {"IVF_FLAT", "BIN_IVF_FLAT"}
    assert idx_params.get("metric_type") in {"COSINE", "HAMMING", "L2"}
    nlist = idx_params.get("nlist") or idx_params.get("params", {}).get("nlist")
    assert nlist is not None and int(nlist) >= 16

    # Basic search to ensure loaded
    try:
        coll.load()
    except Exception as exc:
        pytest.fail(f"Failed to load collection '{COLL}': {exc}")
    coll.search(
        data=[[0.0, 0.0, 0.0, 0.0][: vector_field.params["dim"]]],
        anns_field=vector_field.name,
        param={
            "metric_type": idx_params.get("metric_type", "COSINE"),
            "params": {"nprobe": 4},
        },
        limit=1,
        expr=None,
    )
