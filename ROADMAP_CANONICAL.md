# Canonical Roadmap — AROMADP Strict‑Mode + Tripartite Integration (2025‑11‑09)

Truth principle: Implemented (I), Partial (P), Not Implemented / Proposed (N). All future items have concrete acceptance tests. No mocks, no alternatives, no disable paths.

## 1) Architecture (High‑Level)

```
+-------------------+      +-------------------+      +---------------------+
|   Client/API      | ---> |   Orchestrator    | ---> |   Predictor Threads  |
| (REST/gRPC)       |      | (Plan phase)      |      | (state/agent/action) |
+-------------------+      +-------------------+      +---------------------+
      |                         |                           |
      v                         v                           v
  +----------------+       +----------------+         +-------------------+
  | reward_prod    |       | segmentation   |         |  integrator_hub   |
  | (Kafka Avro)   |       | (HMM wrapper)  |         |  (fusion, OPA)    |
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
- Transport: Kafka KRaft, Avro mandatory; Redis, Postgres, OPA required.
- Single image policy (I). Shadow/eval routing (I).
- Runtime dedup and central libs planned (N).

## 2) Contracts & Topics (Avro)

Implemented (I): belief_update, global_frame, segment_boundary, integrator_context, reward_event (r_user).

Partial (P): next_event (error/attribution labeling), config_update (τ + λ_d fields in use, attribution incomplete).

Proposed (N):
- predictor_calibration (ECE, Brier, T_d, ts)
- fusion_drift_event (entropy/regret signature)
- config_update per‑domain λ_d extension

Canonical topics
- Inputs: cog.state.updates, cog.agent.updates, cog.action.updates
- Core: cog.global.frame, cog.segments, cog.integrator.context
- Learning: soma.reward.events, soma.next.events, soma.config.updates

## 3) Consolidation & Single Entry

Duplication (P): per‑service bootstrap/serde/encode/tracing; NextEvent builders.

Actions (N):
- `common/kafka.py`: producer/consumer factory, registry, serde cache, health
- `common/events.py`: next_event builder, regret, attribution (λ_d, γ_d)
- `common/observability.py`: metrics/tracing init and registry
- `services/entry.py`: single dispatcher; removes per‑service mains duplication

Acceptance
- Predictors import shared libs; no local encode/serde; ≥20% CLoC reduction in mains.

## 4) Mathematical Foundations

Predictor Threads (I): shared diffusion backend (chebyshev/lanczos), error metrics.

Fusion Normalization (N):
- e_norm_d = (error_d−μ_d)/(σ_d+ε)
- w_d = softmax(−α·e_norm_d), α adaptive via regret feedback

Calibration (N):
- Temperature T_d; ECE/Brier metrics; gated updates

Consistency (P):
- κ = 1 − JSD(...); inconsistency alerts planned

Segmentation HMM (N):
- 2‑state HMM over binary salience; online Viterbi; ≤2‑tick latency

Regret (P→N):
- regret_d = max(0,c_target_d−c’_d); aggregate Σ γ_d·regret_d; learner maintains c_target_d

## 5) Reward & Attribution

Implemented (P): reward_event components; r_user path.

Proposed (N): components normalization; learn β_i; infer γ_d; emit λ_d in config_update.

Acceptance
- λ_d adjustments reduce domain regret ≥5% without entropy breach.

## 6) Observability & SLOs

Implemented (I/P): health/metrics base, drift metrics, segmentation metrics.

Add (N): normalized_error_d, fusion_weight_d, α, ECE_d, Brier_d, κ, P(TRANSITION), drift gauges.

Alerts (N): Calibration Drift, Fusion Weight Instability, Consistency Degradation, Segmentation Flood/Drought, Drift Trigger.

Dashboards (N): predictor quality, fusion stability, segmentation HMM, learning (τ, λ_d, α, regret).

## 7) Feature Flags (values‑gated, not infra)

Existing (I): ENABLE_COG_THREADS, SOMA_HEAT_METHOD.

Add (N): ENABLE_FUSION_NORMALIZATION, ENABLE_HMM_SEGMENTATION, ENABLE_CALIBRATION, ENABLE_CONSISTENCY_CHECKS.

## 8) Sprints & Acceptance Tests

- Sprint 0 Foundations (Done)
- Sprint 1 Reward Ingestion (Done)
- Sprint 2 Next‑Event Heads (Partial)
- Sprint 3 Online Learner Loop (Partial)
- Sprint 4 OPA & Shadow (Done)
- Sprint 5 Observability Base (Done)
- Sprint 6 Canary & Rollout (Pending)
- Sprint 7 Fusion Normalization (N)
- Sprint 8 Consolidation & Single Entry (N)
- Sprint 9 HMM Segmentation (N)
- Sprint 10 Calibration Pipeline (N)
- Sprint 11 Consistency Metrics (P)
- Sprint 12 Reward Attribution (N)
- Sprint 13 Drift & Auto‑Rollback (N)

## 9) Production Readiness & Ops

Hardening (N): unified health schema, graceful shutdown, bounded queues, integrator SLA.

Playbooks (N): calibration drift, segmentation flood/drought, κ degradation, OPA latency spikes.

## 10) Risks & Mitigations

- α overfit → bounds + EMA; Calibration sparsity → min samples; HMM latency → priors; Metric sprawl → namespace; Coupling latency → async checks.

## 11) Non‑Goals / Constraints

- Remain single image; no heavy online deep training; no persistent per‑user state beyond memory.

## 12) Rollback Plan

Disable advanced flags; revert via orchestrator; automatic rollback on drift trigger.

## 13) Status Summary (I/P/N) — Updated 2025-11-10

- Diffusion (I), Integrator softmax (P), NextEvent emit (P), Reward ingest (P), Tau updates (I), OPA+shadow (P), Observability base (I), HMM (P), Fusion normalization (P), Calibration (P+), Consistency (P), Attribution λ_d (P), Consolidation (P), Drift automation (P).

## 14) AROMADP Strict‑Mode Enforcement (Truthful Inventory)

- Kafka: KRaft broker configured; hard‑fail connect; standardized on confluent‑kafka (legacy kafka‑python removed from services).
- Avro‑only: Encode paths are Avro‑only across services; residual JSON decoding only for internal payload parsing (no network path). Add/maintain invariant tests to block regressions.
- Redis/Postgres: Required; no fakeredis/SQLite alternatives in code paths.
- OPA: Integrator uses fail‑closed posture; ensure readiness asserts when OPA configured; add latency SLO and alerts.
- Tracing/Metrics: Enforce provider; spans added across integrator/segmentation; extend to predictors.
- Invariant audit: Add CI scanner for banned keywords ("fakeredis", "noop tracer", "disable_auth", "sqlite://", "KafkaProducer" from kafka‑python).

Acceptance (Strict‑mode): zero banned keywords; Avro round‑trips for all schema topics; startup health abort ≤5s on infra failure; dashboards populated for α/entropy/regret/κ/ECE/segmentation; drift rollback only via real events; predictor mains CLoC −20%.

## 15) Next‑Gen Spec Sync (Gaps & Plan)

- Teach: TeachFeedback→RewardEvent (I); TeachCapsule topic pending (N); Avro‑only enforcement pending.
- Env: SOMA_HEAT_METHOD (I); SOMA_EXPV_METHOD/USE_MLA pending (N).
- Integrator: dwell/entropy_cap gating missing (N); leader flips metric exists (I); entropy metrics (I).
- Segmentation: max dwell present (P); dedupe/write‑gap and rate metrics pending (N).
- Retrieval: hit rate, p95 latency metrics pending (N); utility indexing pending (N).
- Reward: add reward_total_with_user_avg (N).
- Diffusion: low‑rank expv pending (N); heat_expv_seconds & rel‑error metrics pending (N).
- MLA‑G: attention path + metric pending (N).
- Tests: Laplacian SPD/expv accuracy/integrator gating/E2E teach→reward Kafka loop (partial to pending).

Planned Work (high‑priority): integrator dwell/entropy gating, segmentation metrics, retrieval instrumentation, diffusion low‑rank + metrics, Avro‑only enforcement across teach/reward.

## 16) Rollout & SLO Gates

Shadow (48–72h) → Canary (10–20%) → GA; SLO: retrieval hit‑rate, latency, contradictions, storage; rollback by alerts.

## 17) Phase Plan (Execution Order)

Phase 0 (Strict‑mode foundations)
- Avro‑only serialization; remove JSON alternatives; standardize on confluent‑kafka; invariant scanner; fail‑fast infra (Kafka/Redis/Postgres/OPA). Status: Ongoing; invariants + OPA readiness next.

Phase 1 (Predictors)
- Add state/agent/action predictors publishing PredictorUpdate with error metrics.

Phase 2 (Integrator)
- Leader election with min_dwell + entropy_cap; GlobalFrame schema; metrics.

Phase 3 (Segmentation HMM)
- Two‑state HMM wrapper; dedupe/write‑gap; boundaries/hour and dup_rate metrics.

Phase 4 (Diffusion & Retrieval)
- Low‑rank expv + rel‑error/runtime metrics; retrieval hit/p95 latency metrics, cache utilization, miss tiers.

Phase 5 (Policy & Security)
- OPA fail‑closed; auth always‑on; alerts + runbooks.

Phase 6 (Observability)
- Tracing enforcement; coverage across diffusion/predictor/integrator/segmentation; finalize dashboards.

All phases conform to AROMADP: no mocks, no disable paths, real infra only.
