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
