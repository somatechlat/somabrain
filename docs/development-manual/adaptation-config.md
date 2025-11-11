# Adaptation & Consistency Development

**Purpose**: Guide contributors extending SomaBrain's adaptive learning, attribution, consistency enforcement (κ), and drift rollback behaviors. Centralizes how parameters are defined, updated, and validated—replacing legacy environment-variable overrides.

**Audience**: Engineers modifying fusion weighting, learning dynamics, consistency thresholds, or drift handling.

---

## Centralized Learning & Runtime Parameters

Adaptive parameters and enforcement thresholds live in a single source of truth (runtime configuration / structured updates):

| Parameter | Source | Description |
|-----------|--------|-------------|
| `learning_rate` | Avro `ConfigUpdate` | Online learner step size for weight adaptation |
| `exploration_temp` (`tau`) | Avro `ConfigUpdate` | Exploration temperature controlling weight diversity |
| `lambda_state` / `lambda_agent` / `lambda_action` (λ_d) | Avro `ConfigUpdate` | Attribution multipliers applied during fusion candidate weighting |
| `gamma_state` / `gamma_agent` / `gamma_action` (γ_d) | Avro `ConfigUpdate` | Secondary attribution signals (diagnostic / experimental) |
| `kappa_min` | `runtime_config` | Minimum acceptable κ similarity (1 − JSD) before enforcement begins |
| `kappa_fail_count` | `runtime_config` | Consecutive frames below threshold required to mark degraded state |
| `kappa_hysteresis` | `runtime_config` | Frames above threshold needed to clear degraded state |
| `consistency_drop_frame` | `runtime_config` | If true drop frames when degraded; if false adjust leader weighting |
| Drift window params | Drift detector config | Entropy/regret windows defining anomaly boundaries |

Legacy `SOMABRAIN_LEARNING_*` environment overrides were removed—do not reintroduce ad-hoc env-based tuning. Use schema-backed updates.

References:
- Schema: `proto/cog/config_update.avsc` (includes tenant + learning + λ_d + γ_d fields).
- Enforcement & fusion logic: `somabrain/services/integrator_hub.py`.
- Runtime overrides scaffolding: `somabrain/runtime_config.py`.
- Drift detection & rollback: `somabrain/monitoring/drift_detector.py`.
- Technical deep dive: `../technical-manual/fusion-consistency-and-drift.md`.

---

## Fusion Weighting Flow

1. Candidate frames produced (agent / state / action distributions).
2. Raw logits normalized with adaptive temperature (`tau`).
3. λ_d multipliers applied to candidate weight exponentials.
4. κ computed (1 − JSD) between agent intent and selected action distribution.
5. Enforcement: if κ below threshold for `kappa_fail_count` frames → degraded state.
6. Degraded handling: frame dropped (if `consistency_drop_frame`) or leader weight adjusted (fallback rationale annotated).
7. Drift detector monitors entropy/regret sequences; triggers rollback → emits `FusionRollbackEvent` + conservative `ConfigUpdate`.

Ensure any modifications preserve rationale annotations for observability (operators need frame-level transparency).

---

## Making Schema Changes

1. Add new fields to Avro with defaults (never breaking existing consumers).
2. Update round-trip tests (`tests/kafka/test_avro_contracts.py`).
3. Extend acceptance tests if new enforcement or telemetry behavior emerges.
4. Document changes in both this page and `fusion-consistency-and-drift.md`.
5. Run fast suite: `pytest -q tests/unit tests/acceptance`.

Do not remove or mutate existing field types without a deprecation plan.

---

## Acceptance Tests (Invariant Coverage)

| Test | Invariant |
|------|-----------|
| `test_calibration_emission.py` | Calibration Avro record emitted when flag enabled |
| `test_hmm_segmentation_metrics.py` | Segmentation metrics gauges registered |
| `test_consistency_enforcement.py` | Low κ → degraded → frame drop / rationale |
| `test_drift_rollback_pipeline.py` | Drift → rollback event + conservative config update |

Guidelines: Patch only producer creation when broker unavailable; never stub out fusion or learner computation.

---

## Extending Attribution Logic

When adding new attribution dimensions (e.g. `lambda_context`):
1. Update Avro schema with default value.
2. Adjust fusion weighting loop to multiply candidate exponentials by new dimension.
3. Add metrics (gauge/histogram) for attribution contribution.
4. Introduce acceptance test asserting influence on final weight distribution under controlled inputs.
5. Document rationale and operational guidance here and in technical manual.

Keep attribution multiplicative and bounded; avoid unscaled additive bias that compromises comparability across candidates.

---

## Consistency (κ) Enforcement Modifications

If refining κ logic:
- Maintain 1 − JSD formulation unless replacing with a strictly superior metric (justify in PR description).
- Preserve hysteresis to avoid enforcement flapping.
- Keep counters (`kappa_below_counts`, enforcement metrics) exposed for operators.
- Update acceptance test with crafted distributions demonstrating new threshold semantics.

---

## Drift Rollback Adjustments

When tuning drift:
1. Modify window sizes or entropy/regret thresholds in drift detector config.
2. Ensure rollback emits conservative `ConfigUpdate` (lower learning rate, moderated temperature) plus event topics.
3. Acceptance test should still observe rollback sequence under synthetic drift scenario.

Rollback conservatism must be explicit—log rationale and annotate resulting frame.

---

## Observability Requirements

Every adaptation/enforcement change must surface:
- Prometheus metrics (rates, counters, gauges) with tenant labels.
- Structured logs including rationale, thresholds, and before/after values.
- Frame annotations summarizing applied multipliers and enforcement decisions.

Missing observability is a blocker for merging adaptation changes.

---

## Contribution Checklist

1. Schema adjusted (if needed) with backward-compatible defaults.
2. Fusion / enforcement logic updated minimally and surgically.
3. Metrics & logging added (no silent changes).
4. Acceptance test added or updated.
5. Technical manual & this page updated.
6. Fast suite passes (`pytest -q tests/unit tests/acceptance`).
7. CI full suite (integration + e2e where applicable) green.

---

**Common Mistakes**:
- Reintroducing env overrides for learning rates (avoid; use runtime config & Avro updates).
- Skipping rationale annotation causing opaque operator view.
- Adding attribution without metrics, breaking weight transparency.

**References**:
- Technical: `../technical-manual/fusion-consistency-and-drift.md`
- Environment Variables: `../technical-manual/environment-variables.md`
- Testing: `testing-guidelines.md`
