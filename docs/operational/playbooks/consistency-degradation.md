# Playbook: Consistency Degradation (κ) — Versioned Runbook

- Symptoms: Alert `ConsistencyKappaLow` (<0.2 over 10m); downstream policy inconsistency.
- Dashboards: Integrator κ gauges/histograms; posterior distributions for agent/action.
- Checks:
  - Validate predictor outputs and recent deployments.
  - Review `somabrain_integrator_candidate_weight` spread and alpha error trend.
- Actions:
  - Increase exploration (tau) via `config_update` for affected tenants.
  - If normalization correlates with instability, disable `ENABLE_FUSION_NORMALIZATION` and note the override.
- Rollback: Revert to softmax-only fusion; clamp α within safe bounds.
- References: `somabrain/services/integrator_hub.py` (`_compute_kappa`), `alerts.yml`.
