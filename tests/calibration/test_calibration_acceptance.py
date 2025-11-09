import random
import os


def test_calibration_acceptance_enforcement(monkeypatch):
    # Enable calibration path and disable Kafka network IO via env flag
    monkeypatch.setenv("ENABLE_CALIBRATION", "1")
    monkeypatch.setenv("SOMABRAIN_DISABLE_KAFKA", "1")

    from somabrain.services.calibration_service import calibration_service
    from somabrain.calibration.calibration_metrics import calibration_tracker

    domain = "state"
    tenant = "public"
    for _ in range(220):
        c = min(0.99, max(0.01, random.uniform(0.6, 0.9)))
        a = max(0.0, min(1.0, c - random.uniform(0.15, 0.25)))
        calibration_service.record_prediction(domain, tenant, c, a)

    pre = calibration_tracker.get_calibration_metrics(domain, tenant)
    calibration_service._maybe_enforce(domain, tenant)
    post = calibration_tracker.get_calibration_metrics(domain, tenant)

    assert post["ece"] <= pre["ece"] + 0.05
    key = f"{domain}:{tenant}"
    assert key in calibration_service._last_good_temperature
