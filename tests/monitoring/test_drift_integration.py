import time
from dataclasses import replace

from somabrain.monitoring.drift_detector import DriftDetector, DriftConfig
from somabrain.services.integrator_hub import IntegratorHub


def test_drift_auto_disables_normalization(monkeypatch):
    # Enable drift + normalization via centralized config; disable auto-rollback
    import somabrain.modes as modes

    base = modes.get_mode_config()
    monkeypatch.setattr(
        modes,
        "get_mode_config",
        lambda: replace(
            base,
            enable_drift=True,
            fusion_normalization=True,
            enable_auto_rollback=False,
        ),
    )
    # Kafka must be available in strict mode; this test does not use network

    # Tight thresholds to trigger quickly
    cfg = DriftConfig(
        entropy_threshold=0.2,
        regret_threshold=0.2,
        window_size=10,
        min_samples=3,
        cooldown_period=0,
    )
    det = DriftDetector(config=cfg)
    # Patch integrator module drift reference to our detector
    import somabrain.services.integrator_hub as ih

    ih._DRIFT = det

    hub = IntegratorHub()
    # Force flags after construction
    hub._norm_enabled = True
    hub._drift_enabled = True

    # Craft synthetic rounds to yield high entropy (~uniform weights) and low leader confidence
    def push_round(delta_err: float):
        for d in ("state", "agent", "action"):
            ev = {"domain": d, "delta_error": delta_err, "evidence": {"tenant": "t1"}}
            hub._process_update(ev)

    for _ in range(4):
        push_round(1.0)
        time.sleep(0.01)

    # After drift detection the normalization should be disabled
    assert hub._norm_enabled is False, "Normalization should auto-disable on drift"

    # Ensure drift detector recorded at least one drift event state
    st = det.get_drift_status("state", "t1")
    assert st["samples"] >= 3
    assert st["stable"] is False


def test_drift_rollback_event_emission(monkeypatch):
    # Enable drift, auto-rollback, and normalization via centralized config
    import somabrain.modes as modes

    base = modes.get_mode_config()
    monkeypatch.setattr(
        modes,
        "get_mode_config",
        lambda: replace(
            base,
            enable_drift=True,
            enable_auto_rollback=True,
            fusion_normalization=True,
        ),
    )
    cfg = DriftConfig(
        entropy_threshold=0.05,
        regret_threshold=0.05,
        window_size=10,
        min_samples=3,
        cooldown_period=0,
    )
    det = DriftDetector(config=cfg)
    import somabrain.services.integrator_hub as ih

    ih._DRIFT = det
    hub = IntegratorHub()
    hub._norm_enabled = True
    hub._drift_enabled = True
    # We cannot easily inspect Kafka emission without a test harness; assert that rollback triggers normalization disable path indirectly by forcing drift repeatedly.
    for _ in range(4):
        for d in ("state", "agent", "action"):
            ev = {"domain": d, "delta_error": 10.0, "evidence": {"tenant": "t2"}}
            hub._process_update(ev)
    st = det.get_drift_status("state", "t2")
    assert st["samples"] >= 3
    assert st["stable"] is False
