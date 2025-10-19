import numpy as np

from somabrain.memory.superposed_trace import SuperposedTrace, TraceConfig
from somabrain.quantum import HRRConfig, QuantumLayer


def test_superposed_trace_handles_thousands_of_memories() -> None:
    dim = 256
    cfg = TraceConfig(dim=dim, eta=0.08, rotation_enabled=True, cleanup_topk=32)
    quantum = QuantumLayer(HRRConfig(dim=dim, seed=21, sparsity=0.1))
    trace = SuperposedTrace(cfg, quantum=quantum)

    rng = np.random.default_rng(123)
    anchors = []
    for idx in range(2000):
        key = rng.normal(size=dim).astype(np.float32)
        value = rng.normal(size=dim).astype(np.float32)
        trace.upsert(f"anchor-{idx}", key, value)
        anchors.append((key, value))

    state_norm = float(np.linalg.norm(trace.state))
    assert abs(state_norm - 1.0) < 1e-4

    sample_key, sample_value = anchors[-1]
    raw = trace.recall_raw(sample_key)
    cosine = float(np.dot(raw / np.linalg.norm(raw), sample_value / np.linalg.norm(sample_value)))
    assert cosine > 0.5
