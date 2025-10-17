from __future__ import annotations

import numpy as np

from somabrain.memory.superposed_trace import SuperposedTrace, TraceConfig


def test_decay_update_preserves_norm_and_decay():
    dim = 8
    cfg = TraceConfig(dim=dim, eta=0.5, rotation_enabled=False)
    trace = SuperposedTrace(cfg)

    key = np.ones(dim, dtype=np.float32)
    value_a = np.arange(1, dim + 1, dtype=np.float32)
    value_b = np.arange(dim, 0, -1, dtype=np.float32)

    trace.upsert("a", key, value_a)
    state_after_a = trace.state

    trace.upsert("b", key, value_b)
    state_after_b = trace.state

    # Expected: normalized average of previous state and new binding
    expected_binding = trace.quantum.bind(
        key / np.linalg.norm(key), value_b / np.linalg.norm(value_b)
    )
    expected_state = 0.5 * state_after_a + 0.5 * expected_binding
    expected_state /= np.linalg.norm(expected_state)

    assert np.allclose(state_after_b, expected_state, atol=1e-5)
    assert abs(np.linalg.norm(state_after_b) - 1.0) < 1e-5


def test_rotation_changes_binding_consistently():
    dim = 16
    key = np.ones(dim, dtype=np.float32)
    value = np.linspace(0.1, 1.6, dim, dtype=np.float32)

    cfg_no_rot = TraceConfig(dim=dim, eta=1.0, rotation_enabled=False)
    trace_no_rot = SuperposedTrace(cfg_no_rot)
    trace_no_rot.upsert("x", key, value)

    cfg_rot = TraceConfig(dim=dim, eta=1.0, rotation_enabled=True, rotation_seed=123)
    trace_rot = SuperposedTrace(cfg_rot)
    trace_rot.upsert("x", key, value)

    # Rotation should change the state compared to the non-rotated binding
    assert not np.allclose(trace_no_rot.state, trace_rot.state)

    # Applying the same rotation twice should be deterministic
    trace_rot_2 = SuperposedTrace(cfg_rot)
    trace_rot_2.upsert("x", key, value)
    assert np.allclose(trace_rot.state, trace_rot_2.state)


def test_cleanup_returns_best_anchor():
    dim = 12
    cfg = TraceConfig(dim=dim, eta=1.0, rotation_enabled=False)
    trace = SuperposedTrace(cfg)

    key = np.ones(dim, dtype=np.float32)
    good_value = np.zeros(dim, dtype=np.float32)
    good_value[0] = 1.0
    bad_value = np.zeros(dim, dtype=np.float32)
    bad_value[1] = 1.0

    trace.register_anchor("good", good_value)
    trace.register_anchor("bad", bad_value)

    trace.upsert("good", key, good_value)

    _, (best_id, best_score, second_score) = trace.recall(key)
    assert best_id == "good"
    assert best_score > second_score
    assert best_score > 0.8
