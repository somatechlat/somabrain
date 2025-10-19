import numpy as np

from somabrain.memory.superposed_trace import SuperposedTrace, TraceConfig
from somabrain.quantum import HRRConfig, QuantumLayer


def _make_layer(dim: int = 256) -> QuantumLayer:
    return QuantumLayer(HRRConfig(dim=dim, seed=13, sparsity=0.1))


def test_decay_and_binding_preserve_state() -> None:
    dim = 64
    cfg = TraceConfig(dim=dim, eta=0.4, rotation_enabled=False)
    trace = SuperposedTrace(cfg, quantum=_make_layer(dim))

    key = np.ones(dim, dtype=np.float32)
    value_a = np.linspace(0.1, 0.9, dim, dtype=np.float32)
    value_b = np.linspace(0.9, 0.1, dim, dtype=np.float32)

    trace.upsert("first", key, value_a)
    state_after_first = trace.state

    trace.upsert("second", key, value_b)
    state_after_second = trace.state

    expected_binding = trace.quantum.bind(
        key / np.linalg.norm(key), value_b / np.linalg.norm(value_b)
    )
    expected_state = (1 - cfg.eta) * state_after_first + cfg.eta * expected_binding
    expected_state /= np.linalg.norm(expected_state)

    assert np.allclose(state_after_second, expected_state, atol=1e-5)
    assert abs(np.linalg.norm(state_after_second) - 1.0) < 1e-5


def test_rotation_is_deterministic() -> None:
    dim = 96
    key = np.random.default_rng(5).normal(size=dim).astype(np.float32)
    value = np.random.default_rng(6).normal(size=dim).astype(np.float32)

    cfg = TraceConfig(dim=dim, eta=1.0, rotation_enabled=True, rotation_seed=123)
    trace_a = SuperposedTrace(cfg, quantum=_make_layer(dim))
    trace_b = SuperposedTrace(cfg, quantum=_make_layer(dim))

    trace_a.upsert("anchor", key, value)
    trace_b.upsert("anchor", key, value)

    assert np.allclose(trace_a.state, trace_b.state, atol=1e-6)


def test_cleanup_recovers_best_anchor() -> None:
    dim = 128
    cfg = TraceConfig(dim=dim, eta=1.0, rotation_enabled=False)
    trace = SuperposedTrace(cfg, quantum=_make_layer(dim))

    rng = np.random.default_rng(11)
    key = np.ones(dim, dtype=np.float32)
    good = rng.normal(size=dim).astype(np.float32)
    good /= np.linalg.norm(good)
    bad = rng.normal(size=dim).astype(np.float32)
    bad /= np.linalg.norm(bad)

    trace.register_anchor("good", good)
    trace.register_anchor("bad", bad)
    trace.upsert("good", key, good)

    _, (anchor_id, best, second) = trace.recall(key)
    assert anchor_id == "good"
    assert best > second
