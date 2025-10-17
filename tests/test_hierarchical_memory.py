from __future__ import annotations

import numpy as np

from somabrain.memory.hierarchical import LayerPolicy, TieredMemory
from somabrain.memory.superposed_trace import TraceConfig


def _vec(dim: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.normal(size=(dim,)).astype(np.float32)


def test_remember_prefers_working_memory_layer():
    wm_cfg = TraceConfig(dim=16, eta=0.5, rotation_enabled=False)
    ltm_cfg = TraceConfig(dim=16, eta=0.2, rotation_enabled=False)
    tiered = TieredMemory(
        wm_cfg,
        ltm_cfg,
        wm_policy=LayerPolicy(threshold=0.5, promote_margin=0.05),
    )

    key = _vec(16, 1)
    value = _vec(16, 2)

    tiered.remember("item", key, value)
    result = tiered.recall(key)

    assert result.layer == "wm"
    assert result.anchor_id == "item"
    assert result.score > 0.9
    assert result.margin > 0.0


def test_recalls_fall_back_to_ltm_when_wm_anchor_missing():
    wm_cfg = TraceConfig(dim=16, eta=0.5, rotation_enabled=False)
    ltm_cfg = TraceConfig(dim=24, eta=0.2, rotation_enabled=False)
    tiered = TieredMemory(
        wm_cfg,
        ltm_cfg,
        wm_policy=LayerPolicy(threshold=0.7, promote_margin=0.05),
        ltm_policy=LayerPolicy(threshold=0.5, promote_margin=0.05),
        promotion_callback=lambda ctx: True,
    )

    key = _vec(24, 42)
    value = _vec(24, 84)

    tiered.remember("concept", key, value)
    tiered.wm.remove_anchor("concept")

    recall_result = tiered.recall(key)

    assert recall_result.layer == "ltm"
    assert recall_result.anchor_id == "concept"
    assert recall_result.score >= 0.5


def test_promotion_callback_can_abort_ltm_storage():
    wm_cfg = TraceConfig(dim=8, eta=0.7, rotation_enabled=False)
    ltm_cfg = TraceConfig(dim=8, eta=0.2, rotation_enabled=False)
    tiered = TieredMemory(
        wm_cfg,
        ltm_cfg,
        promotion_callback=lambda ctx: False,
    )

    key = _vec(8, 7)
    value = _vec(8, 9)

    tiered.remember("topic", key, value)

    assert "topic" not in tiered.ltm.anchors

    tiered.wm.remove_anchor("topic")
    recall_result = tiered.recall(key)

    assert recall_result.layer == "wm"
    assert recall_result.score == 0.0
    assert recall_result.anchor_id == ""
