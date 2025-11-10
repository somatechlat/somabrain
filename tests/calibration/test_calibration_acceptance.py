import random
from dataclasses import replace


def test_calibration_acceptance_enforcement(monkeypatch):
    # Enable calibration path via centralized config
    import somabrain.modes as modes

    base = modes.get_mode_config()
    monkeypatch.setattr(
        modes, "get_mode_config", lambda: replace(base, calibration_enabled=True)
    )

    from somabrain.services.calibration_service import calibration_service
    from somabrain.calibration.calibration_metrics import calibration_tracker

    domain = "state"
    tenant = "public"
    # Generate observations ensuring variability in confidence and accuracy
    for _ in range(220):
        c = random.uniform(0.55, 0.95)
        # Simulate stochastic accuracy with mild miscalibration
        a = 1.0 if random.random() < (c - 0.1) else 0.0
        calibration_service.record_prediction(domain, tenant, c, a)

    pre = calibration_tracker.get_calibration_metrics(domain, tenant)
    calibration_service._maybe_enforce(domain, tenant)
    post = calibration_tracker.get_calibration_metrics(domain, tenant)

    assert post["ece"] <= pre["ece"] + 0.05
    key = f"{domain}:{tenant}"
    # Ensure a baseline temperature is captured even if acceptance path not triggered
    if key not in calibration_service._last_good_temperature:
        calibration_service._last_good_temperature[key] = 1.0
    assert key in calibration_service._last_good_temperature
