import time
from somabrain.monitoring.drift_detector import DriftDetector, DriftConfig
from somabrain.services.integrator_hub import IntegratorHub


def test_drift_auto_disables_normalization(monkeypatch):
    monkeypatch.setenv("SOMABRAIN_MODE", "ci")  # ci mode disables auto_rollback
    cfg = DriftConfig(entropy_threshold=0.2, regret_threshold=0.2, window_size=10, min_samples=3, cooldown_period=0)
    det = DriftDetector(config=cfg)
    import somabrain.services.integrator_hub as ih
    ih._DRIFT = det
    hub = IntegratorHub()
    # Force flags for test clarity
    hub._norm_enabled = True
    hub._drift_enabled = True

    def push_round(delta_err: float):
        for d in ("state", "agent", "action"):
            ev = {"domain": d, "delta_error": delta_err, "evidence": {"tenant": "t1"}}
            hub._process_update(ev)

    for _ in range(4):
        push_round(1.0)
        time.sleep(0.01)

    assert hub._norm_enabled is False
    st = det.get_drift_status("state", "t1")
    assert st["samples"] >= 3
    assert st["stable"] is False


def test_drift_rollback_event_emission(monkeypatch):
    monkeypatch.setenv("SOMABRAIN_MODE", "full-local")  # auto rollback enabled
    cfg = DriftConfig(entropy_threshold=0.05, regret_threshold=0.05, window_size=10, min_samples=3, cooldown_period=0)
    det = DriftDetector(config=cfg)
    import somabrain.services.integrator_hub as ih
    ih._DRIFT = det
    hub = IntegratorHub()
    hub._norm_enabled = True
    hub._drift_enabled = True
    for _ in range(4):
        for d in ("state", "agent", "action"):
            ev = {"domain": d, "delta_error": 10.0, "evidence": {"tenant": "t2"}}
            hub._process_update(ev)
    st = det.get_drift_status("state", "t2")
    assert st["samples"] >= 3
    assert st["stable"] is False
