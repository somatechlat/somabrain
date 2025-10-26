from __future__ import annotations

import numpy as np

from somabrain.services.tiered_memory_registry import TieredMemoryRegistry


def test_tiered_registry_remember_and_recall_simple() -> None:
    reg = TieredMemoryRegistry()
    tenant, ns = "test", "unit"
    # Create a simple 8-D key/value
    key = np.asarray([1, 0, 0, 0, 0, 0, 0, 0], dtype=np.float32)
    val = np.asarray([1, 0, 0, 0, 0, 0, 0, 0], dtype=np.float32)
    payload = {"task": "unit-key"}

    reg.remember(tenant, ns, anchor_id="a1", key_vector=key, value_vector=val, payload=payload, coordinate=[0,0,0])

    # Query close to the anchor
    q = np.asarray([0.99, 0.01, 0, 0, 0, 0, 0, 0], dtype=np.float32)
    res = reg.recall(tenant, ns, query_vector=q)
    assert res is not None
    assert res.context.anchor_id == "a1"
    assert res.context.score >= 0.5
    # Margin should be non-negative and small but present in trivial case
    assert res.context.margin >= 0.0
    # Expose eta/sparsity/backend for observability
    assert 0.0 <= res.eta <= 1.0
    assert res.sparsity >= 0.0
    assert isinstance(res.backend, str)
import numpy as np

from somabrain.quantum import HRRConfig, QuantumLayer
from somabrain.services.config_service import ConfigEvent
from somabrain.services.tiered_memory_registry import TieredMemoryRegistry


def _quantum(dim: int = 256) -> QuantumLayer:
    return QuantumLayer(HRRConfig(dim=dim, seed=17, sparsity=0.1))


def test_remember_and_recall_round_trip() -> None:
    registry = TieredMemoryRegistry()
    q = _quantum(128)

    tenant = "acme"
    namespace = "wm"

    key_vec = q.encode_text("query::alpha")
    value_vec = q.encode_text("payload::alpha")
    payload = {"text": "alpha payload", "importance": 0.9}
    coord = [0.1, 0.2, 0.3]

    registry.remember(
        tenant,
        namespace,
        anchor_id="alpha-anchor",
        key_vector=key_vec,
        value_vector=value_vec,
        payload=payload,
        coordinate=coord,
    )

    result = registry.recall(tenant, namespace, key_vec)
    assert result is not None
    assert result.payload == payload
    assert result.coordinate == coord
    assert result.context.score > 0.8
    assert result.eta == registry._bundles[(tenant, namespace)].wm_cfg.eta


def test_apply_effective_config_updates_runtime() -> None:
    registry = TieredMemoryRegistry()
    q = _quantum(64)
    tenant = "acme"
    namespace = "knowledge"

    registry.remember(
        tenant,
        namespace,
        anchor_id="beta",
        key_vector=q.encode_text("beta key"),
        value_vector=q.encode_text("beta value"),
        payload={"text": "beta"},
        coordinate=None,
    )

    event = ConfigEvent(
        version=1,
        tenant=tenant,
        namespace=namespace,
        payload={
            "eta": 0.2,
            "sparsity": 0.6,
            "cleanup": {"topk": 8, "hnsw": {"efSearch": 64}},
            "gate": {"tau": 0.55},
        },
    )

    applied = registry.apply_effective_config(event)
    assert applied is not None
    assert 0.19 <= applied["eta"] <= 0.21
    assert applied["sparsity"] == 0.6
    assert applied["tau"] == 0.55
