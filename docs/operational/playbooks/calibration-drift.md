# Playbook: Calibration Drift (Versioned Runbook)

- Symptoms: Rising `somabrain_calibration_ece`; alert `CalibrationDrift` firing; downgrade counter increments.
- Dashboards: Calibration view (ECE pre/post, temperature, samples) per domain/tenant.
- Immediate Actions:
  - Verify sample counts (>=200) and class balance; check model version changes.
  - Confirm `ENABLE_CALIBRATION=1` and service health.
  - Inspect downgrade counter and `last_good_temperature` map.
- Remediation:
  - Open recalibration window: gather fresh observations; tune `temperature_scaler.min_samples` if convergence slow.
  - If unresolved after two windows, pin temperature to `last_good_temperature` and file incident follow-up.
- Rollback:
  - Temporarily disable enforcement via feature flag; document timestamp and reason in incident log.
- References: `somabrain/services/calibration_service.py` (acceptance logic), alerts.yml (rule), metrics dashboard.
