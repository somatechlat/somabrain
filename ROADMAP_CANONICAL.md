# Canonical Roadmap — Unified Cognitive Thread, Learning Layer, Tripartite Math, Consolidation

Truth principle: Implemented (I), Partial (P), Not Implemented / Proposed (N). All future items have concrete acceptance tests; everything values-gated; single Docker image; no placeholders.

## 1) Architecture (High-Level)

```
+-------------------+      +-------------------+      +---------------------+
|   Client/API      | ---> |   Orchestrator    | ---> |   Predictor Threads  |
| (REST/gRPC)       |      | (Plan phase)      |      | (state/agent/action) |
+-------------------+      +-------------------+      +---------------------+
	  |                         |                           |
	  v                         v                           v
  +----------------+       +----------------+         +-------------------+
  | reward_prod    |       | segmentation   |         |  integrator_hub   |
  | (Kafka)        |       | (HMM formal)   |         |  (fusion, OPA)    |
  +----------------+       +----------------+         +-------------------+
	  |                         |                           |
	  v                         v                           v
  +---------------------------------------------------------------------+
  |                       learner_online (Bandit/RL)                    |
  |  consumes: reward_event, next_event, integrator_context             |
  |  produces: config_update (tau, λ_d), calibration, drift events      |
  +---------------------------------------------------------------------+
```

Notes
- Transport: Kafka; OPA is HTTP with short timeouts; optional Redis cache (I/P).
- Shadow ratio routes eval traffic (I).
- Single image policy enforced (I).
- Consolidated runtime/entry utilities to remove duplication (N).

## 2) Contracts & Topics (Avro)

Implemented (I): belief_update, global_frame, segment_boundary, integrator_context.

Partial (P): next_event (error field labeling), reward_event (component set), config_update (tau + λ_d attribution fields populated by learner).

Proposed (N):
- predictor_calibration (ECE, Brier, T_d, ts)
- fusion_drift_event (entropy+regret signature)
- config_update extension with per-domain λ_d

Canonical topics
- Inputs: cog.state.updates, cog.agent.updates, cog.action.updates
- Core: cog.global.frame, cog.segments, cog.integrator.context
- Learning: soma.reward.events, soma.next.events, soma.config.updates

## 3) Consolidation & Single Entry

Current duplication (P): per-service `_bootstrap`, `_make_producer`, `_serde`, `_encode`, tracing init, NextEvent construction.

Actions (N):
- `common/kafka.py` for producer, topic names, Avro serde cache
- `common/events.py` for NextEvent builder and regret calculation
- `common/observability.py` thin wrapper around provider
- `services/entry.py` dispatcher for single entry based on env (ENABLE_COG_THREADS)

Acceptance
- Predictors import shared modules; no local encode/serde; CLoC in predictor mains reduced ≥20%.

## 4) Mathematical Foundations

Predictor Threads (I): diffusion backbone emitting (delta_error, confidence).

Fusion Normalization (N):
- e_norm_d = (error_d − μ_d)/(σ_d+ε)
- w_d = exp(−α·e_norm_d)/Σ exp(−α·e_norm_k), α in [α_lo, α_hi]
- α adaptive via learner: α_{t+1} = clip(α_t + η·(regret_mean − target), bounds)

Calibration (N):
- Temperature scaling T_d; metrics ECE_d, Brier_d; update only with min samples

Consistency (P):
- κ = 1 − JSD(P_action|agent || empirical); inconsistency_rate alert >3%

Segmentation HMM (N):
- States: STABLE, TRANSITION; Observations: entropy_delta, error_delta, dwell_norm
- Online Viterbi; boundary when P(TRANSITION) > τ_seg; latency ≤2 ticks

Regret (P→N):
- regret_d = max(0, c_target_d − c'_d); aggregate Σ γ_d·regret_d; learner maintains c_target_d

## 5) Reward & Attribution

Implemented (P): reward_event ingestion with components.

Proposed (N):
- Normalize components; learn β_i; derive γ_d domain attribution; emit λ_d in config_update

Acceptance
- λ_d adjustments reduce domain regret ≥5% vs baseline without raising entropy beyond threshold.

## 6) Observability & SLOs

Implemented (I/P): health/metrics; planning latency histogram + p99 gauge; regret EWMA; OPA veto ratio; entropy; predictor emits and error histogram.

Add (N):
- normalized_error_d gauge; fusion_weight_d; α; ECE_d; Brier_d; κ; P(TRANSITION); drift gauge

Alerts (augment) (N):
- Calibration Drift (ECE_d > threshold); Fusion Weight Instability; Consistency Degradation; Segmentation Flood/Drought; Drift Trigger (entropy band + regret spike)

Dashboards (extend) (N): predictor quality, fusion stability, segmentation state, learning (tau, λ_d, α, regret)

## 7) Feature Flags (values-gated)

Existing (I): ENABLE_COG_THREADS, SOMABRAIN_FF_PREDICTOR_*, learnerEnabled.

Add (N): ENABLE_FUSION_NORMALIZATION, ENABLE_HMM_SEGMENTATION, ENABLE_CALIBRATION, ENABLE_CONSISTENCY_CHECKS, ENABLE_RUNTIME_CONSOLIDATION.

## 8) Sprints & Acceptance Tests

Sprint 0 Foundations (Done)
Sprint 1 Reward Ingestion (Done)
Sprint 2 Next-Event Heads (Partial): Include error metric labeling; acceptance: learner consumes; predictor error gauge <0.05 in controlled tests.
Sprint 3 Online Learner Loop (Partial): Tau live updates; config_update extended with λ_d emission (inverse regret EMA per tenant, provisional mapping).
Sprint 4 OPA & Shadow (Done): Shadow ~5%; veto metric increments; decision latency within SLO.
Sprint 5 Observability Base (Done): Metrics + base alerts.
Sprint 6 Canary & Rollout (Pending): p99 ≤22ms; regret ≤0.05; entropy stable; veto ≤5%.
Sprint 7 Fusion Normalization (N): w_d via exp(−α·e_norm_d); α adaptive; entropy within band; regression <2%.
Sprint 8 Consolidation & Single Entry (N): Predictors import shared utils; no local encode; CLoC drop ≥20%.
Sprint 9 HMM Segmentation (N): Boundary F1 ≥0.9 (synthetic), false boundary <5%, latency ≤2 ticks.
Sprint 10 Calibration Pipeline (N): ECE reduction ≥30%; temperature updates persisted; downgrade on breach.
Sprint 11 Consistency Metrics (Partial): feasibility gauge (binary) emitted; future κ histogram & alerting pending.
Sprint 12 Reward Attribution (N): γ_d published; λ_d adjusts exploration; regret improves ≥5%.
Sprint 13 Drift & Auto-Rollback (N): drift event triggers disable advanced fusion; stabilize within 2 windows.

## 9) Production Readiness & Ops

Hardening (N): unified health schema; graceful shutdown across producer/tracer; bounded queues; SLA tracking for segmentation/integrator.

Playbooks (N): calibration drift; consistency alert; segmentation flood; drift rollback; OPA latency spikes.

## 10) Risks & Mitigations

- Overfitting α → bounds + EMA smoothing.
- Calibration sparsity → minimum sample gate and fallback.
- HMM latency → start with fixed priors; fallback to heuristic.
- Metric sprawl → namespace discipline and pruning.
- Coupling latency → async consistency checks; fail-open until stable.

## 11) Non-Goals / Constraints

- No multi-image split; remain single image.
- No heavy online deep training.
- No persistent per-user state beyond current memory subsystem.

## 12) Rollback Plan

Disable advanced flags individually; full revert with `featureFlags.enableCogThreads=false` and `learnerEnabled=false`. Automated rollback on drift trigger.

## 13) Status Summary (I/P/N)

- Diffusion predictors (I), Integrator softmax (I/P), NextEvent emit (I/P), Reward ingest (P), Tau updates (P), OPA+shadow (I), Observability base (I), HMM (N), Fusion normalization (N), Calibration (N), Consistency (P), Attribution λ_d (P), Consolidation (N), Drift automation (N).

This canonical roadmap unifies implementation, math upgrades, consolidation, and production criteria in a single, truth-based plan.
