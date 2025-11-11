# Fusion, Consistency, and Drift (Strict Mode)

Purpose: Document the strict-mode fusion pipeline in the Integrator Hub, consistency (κ) enforcement, attribution via `config_update`, and drift automation with rollback. This page is the operator and developer reference for runtime behavior, flags, metrics, and schemas.

Audience: SREs, platform engineers, service owners, and developers contributing to cognition services.

---

## Overview

The Integrator Hub fuses predictor domains (`state`, `agent`, `action`) into a single Global Frame. In strict mode:

- Confidence normalization uses an exponential map from per-domain delta error: `conf = exp(-alpha * e_norm)`
- Fusion weights come from a softmax over normalized errors, optionally multiplied by attribution multipliers `λ_d` (per-tenant, per-domain) received via `config_update`.
- Adaptive alpha aims for a target regret by adjusting `alpha` online.
- Consistency κ between agent intent and next action is monitored; persistent κ below a threshold enforces policy (drop or adjust frames).
- Drift detection monitors entropy and regret to auto-disable normalization and emit rollback events and conservative `config_update`.

---

## ConfigUpdate Schema (Avro)

File: `proto/cog/config_update.avsc`

Fields:

- `tenant: string` — Target tenant (default `public`)
- `learning_rate: float` — Learner-proposed LR
- `exploration_temp: float` — Tau for domain softmax (Integrator’s SoftmaxIntegrator)
- `lambda_state|lambda_agent|lambda_action: [null, float]` — Per-domain attribution multipliers λ_d
- `gamma_state|gamma_agent|gamma_action: [null, float]` — Optional attribution shares (telemetry)
- `ts: string` — ISO-8601 timestamp

Producers:

- `LearnerService` (topic `cog.config.updates`): emits tenant, tau, LR, derived λ_d and γ_d from observed regret and reward decomposition.
- `DriftDetector` (on rollback): emits conservative record to reduce exploration.

Consumers:

- `IntegratorHub`: persists λ_d per tenant and multiplies them into fused candidate weights.

---

## Fusion Normalization & Adaptive Alpha

Location: `somabrain/services/integrator_hub.py`

- Normalization computes per-domain z-score of `delta_error` and maps to confidence with `alpha`.
- Candidate weights: `w_d ∝ exp(-alpha * e_norm_d) * λ_d`. Missing λ_d defaults to `1.0`.
- Weights are normalized over available domains; leader is `argmax_d w_d`.
- Adaptive alpha updates after each fused step to reduce regret proxy `1 - max_d w_d` toward a target (`integrator_target_regret`).

Flags (runtime_config defaults):

- `integrator_enforce_conf`: Normalize confidence from error when input confidence is missing/invalid (default true).
- `integrator_alpha`, `integrator_alpha_min|max|eta`, `integrator_target_regret` — Adaptive alpha parameters.

Metrics:

- `somabrain_integrator_alpha`, `*_alpha_target`, `*_alpha_error`, `*_alpha_hist`
- `somabrain_integrator_candidate_weight{tenant,domain}` — Post-λ_d candidate weights
- `somabrain_integrator_fusion_softmax_weight{tenant,domain}` — Final weights (when normalization path active)
- `somabrain_integrator_regret_observed` — Regret proxy histogram

---

## Consistency (κ) Enforcement

Definition: κ = 1 − JSD(P_agent || P_action) for aligned probability maps (intent vs action). Implemented in `_compute_kappa`.

Behavior:

- Track κ per-tenant; when below `consistency_kappa_min` for `consistency_fail_count` consecutive samples, mark tenant as degraded.
- Enforcement when degraded and leader=`action`:
  - If `consistency_drop_frame`: drop the frame (fail-closed).
  - Else: re-route leader to most confident non-action domain and annotate rationale.
- Recovery requires κ ≥ (min + hysteresis).

Flags (`somabrain/runtime_config.py`):

- `consistency_kappa_min` (default 0.55), `consistency_fail_count` (3), `consistency_kappa_hysteresis` (0.05)
- `consistency_drop_frame` (default true), `consistency_alert_enabled` (true)

Metrics:

- `somabrain_integrator_kappa{tenant}`, `*_kappa_hist{tenant}`
- `somabrain_integrator_kappa_threshold`
- `somabrain_integrator_consistency_violations_total{tenant}`
- `somabrain_integrator_consistency_enforced_total{tenant}`

Tests:

- `tests/acceptance/test_consistency_enforcement.py` — Simulates low κ and verifies enforcement.

---

## Drift Detection & Auto-Rollback

Location: `somabrain/monitoring/drift_detector.py`

Detection:

- Maintains rolling windows of entropy and regret. Thresholds can be adaptive (EMA baselines) or fixed.
- On drift: records metrics, persists state, and if auto-rollback is enabled, emits:
  - `FusionRollbackEvent` (`proto/cog/fusion_rollback_event.avsc`)
  - Conservative `ConfigUpdate` to reduce exploration (low tau, LR) with explicit tenant.

Topics (see `somabrain/common/kafka.py`):

- `cog.fusion.drift.events`, `cog.fusion.rollback.events`, `cog.config.updates`

Metrics:

- `somabrain_drift_events_total{domain,tenant,type}`
- `somabrain_rollback_events_total{domain,tenant,trigger}`
- `somabrain_drift_entropy{domain,tenant}`, `somabrain_drift_regret{domain,tenant}`

Tests:

- `tests/acceptance/test_drift_rollback_pipeline.py` — Verifies drift triggers rollback and config_update emissions.
- `tests/monitoring/test_drift_integration.py` — Validates integrator interplay (auto-disables normalization on drift).

---

## Operational Guidance

Troubleshooting:

- If frames drop due to κ enforcement, inspect `*_consistency_violations_total` and κ gauges, then validate predictor outputs alignment.
- If drift repeatedly disables normalization, inspect entropy caps and predictor error distributions; consider raising `integrator_target_regret` cautiously.
- Use `FeatureFlags.set_overrides(["fusion_normalization", "consistency_checks", "calibration"])` for emergency stabilization in local mode. In production, prefer Git-managed config changes.

Rollbacks:

- Confirm `FusionRollbackEvent` and conservative `ConfigUpdate` emissions in Kafka during incidents.
- Ensure tenants are labeled correctly; `tenant` is now part of `ConfigUpdate` and drift events.

Change Management:

- Any schema change must be accompanied by a test in `tests/kafka/test_avro_contracts.py` and updates here.
- Keep `docs/technical-manual/configuration.md` in sync with new flags.
