from __future__ import annotations

import numpy as np
import pytest

from somabrain.services.config_service import ConfigEvent
from somabrain.services.tiered_memory_registry import TieredMemoryRegistry


def test_tiered_memory_registry_roundtrip():
    registry = TieredMemoryRegistry()
    tenant = "acme"
    namespace = "wm"
    anchor_id = "memory-1"
    vector = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    payload = {"text": "note", "coordinate": [0.1, 0.2, 0.3]}

    registry.remember(
        tenant,
        namespace,
        anchor_id=anchor_id,
        key_vector=vector,
        value_vector=vector,
        payload=payload,
        coordinate=payload["coordinate"],
    )

    off_vector = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    registry.remember(
        tenant,
        namespace,
        anchor_id="memory-2",
        key_vector=off_vector,
        value_vector=off_vector,
        payload={"text": "other"},
        coordinate=[0.0, 0.0, 0.0],
    )

    result = registry.recall(tenant, namespace, vector)
    assert result is not None
    assert result.context.anchor_id == anchor_id
    assert result.payload is not None
    assert result.payload["text"] == "note"
    assert result.coordinate == payload["coordinate"]
    assert result.context.score >= 0.0
    assert 0.0 < result.eta <= 1.0
    assert result.sparsity == 1.0

    event = ConfigEvent(
        version=2,
        tenant=tenant,
        namespace=namespace,
        payload={
            "eta": 0.12,
            "cleanup": {"topk": 8},
            "sparsity": 0.5,
            "gate": {"tau": 0.7},
        },
    )
    metrics = registry.apply_effective_config(event)
    assert metrics is not None
    assert metrics["eta"] == pytest.approx(0.12)
    assert metrics["sparsity"] == pytest.approx(0.5)
    assert metrics["tau"] == pytest.approx(0.7)

    updated = registry.recall(tenant, namespace, vector)
    assert updated is not None
    assert updated.tau == pytest.approx(0.7)
