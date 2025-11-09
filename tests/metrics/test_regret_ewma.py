import importlib


def test_regret_ewma_smoothing(monkeypatch):
    m = importlib.import_module("somabrain.metrics")
    alpha = getattr(m, "_REGRET_ALPHA", 0.15)
    # Reset internal state
    if hasattr(m, "_regret_ema"):
        m._regret_ema.clear()
    tenant = "sandbox"
    # First sample initializes EMA
    m.record_regret(tenant, 0.2)
    first = m._regret_ema[tenant]
    assert abs(first - 0.2) < 1e-9
    # Second sample applies smoothing
    m.record_regret(tenant, 0.8)
    second = m._regret_ema[tenant]
    expected_second = alpha * 0.8 + (1 - alpha) * 0.2
    assert abs(second - expected_second) < 1e-9
    # Third sample
    m.record_regret(tenant, 0.5)
    third = m._regret_ema[tenant]
    expected_third = alpha * 0.5 + (1 - alpha) * expected_second
    assert abs(third - expected_third) < 1e-9
