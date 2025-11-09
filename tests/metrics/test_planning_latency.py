import time
import importlib


def test_planning_latency_p99_updates(monkeypatch):
    m = importlib.import_module("somabrain.metrics")
    # Reset internal sample buffer if present
    if hasattr(m, "_planning_samples"):
        m._planning_samples.clear()
    if hasattr(m, "PLANNING_LATENCY_P99"):
        # Feed deterministic latencies
        samples = [0.001, 0.002, 0.003, 0.010, 0.020, 0.030, 0.040, 0.050]
        for s in samples:
            m.record_planning_latency("bfs", s)
        # Compute expected p99 index
        ordered = sorted(samples)
        idx = max(0, int(0.99 * (len(ordered) - 1)))
        expected = ordered[idx]
        # Collector stores value internally; fetch via registry sample
        # The Gauge object has _value attribute in prometheus_client
        g = m.PLANNING_LATENCY_P99
        val = None
        try:
            val = float(g._value.get())  # type: ignore[attr-defined]
        except Exception:  # pragma: no cover
            pass
        assert val is not None
        assert abs(val - expected) < 1e-9
