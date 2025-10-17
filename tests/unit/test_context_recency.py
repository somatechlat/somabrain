import math

from somabrain.context_hrr import HRRContext, HRRContextConfig
from somabrain.quantum import HRRConfig, QuantumLayer


def _make_context(decay_lambda: float = 0.0, min_confidence: float = 0.0):
    layer = QuantumLayer(HRRConfig(dim=64, seed=7))
    current_time = [0.0]

    def now() -> float:
        return current_time[0]

    cfg = HRRContextConfig(
        max_anchors=8,
        decay_lambda=decay_lambda,
        min_confidence=min_confidence,
    )
    ctx = HRRContext(layer, cfg, context_id="test", now_fn=now)
    return ctx, layer, current_time


def test_cleanup_prefers_recent_anchor():
    half_life_sec = 60.0
    decay_lambda = math.log(2.0) / half_life_sec
    ctx, layer, current = _make_context(decay_lambda=decay_lambda)

    current[0] = 0.0
    vec_old = layer.random_vector()
    ctx.admit("old", vec_old, timestamp=current[0])

    current[0] = 120.0  # two half-lives later
    vec_new = layer.random_vector()
    ctx.admit("new", vec_new, timestamp=current[0])

    query = vec_new + 0.05 * layer.random_vector()
    current[0] = 180.0
    best_id, score = ctx.cleanup(query)

    assert best_id == "new"
    assert score > 0.45


def test_cleanup_respects_min_confidence_threshold():
    ctx, layer, current = _make_context(min_confidence=0.8)

    current[0] = 0.0
    vec = layer.random_vector()
    ctx.admit("anchor", vec, timestamp=current[0])

    # Query deliberately orthogonal / opposite to trigger rejection
    query = -vec
    best_id, score = ctx.cleanup(query)

    assert best_id == ""
    assert score == 0.0


def test_capacity_metrics_update_after_admit():
    ctx, layer, current = _make_context()
    current[0] = 10.0

    for idx in range(4):
        ctx.admit(f"a{idx}", layer.random_vector(), timestamp=current[0] + idx)

    anchor_count, max_anchors = ctx.stats()
    assert anchor_count == 4
    assert max_anchors == 8


def test_cleanup_analysis_exposes_margin():
    ctx, layer, current = _make_context()
    current[0] = 1.0
    v1 = layer.random_vector()
    v2 = layer.random_vector()
    ctx.admit("a", v1, timestamp=current[0])
    current[0] = 2.0
    ctx.admit("b", v2, timestamp=current[0])

    query = v1 + 0.1 * v2
    result = ctx.cleanup(query)

    assert hasattr(result, "margin")
    assert result.margin >= 0.0
