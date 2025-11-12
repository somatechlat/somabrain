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

## 18) Centralized Test Suite (Sprint T0) — Added 2025-11-11

Goals
- Eliminate scattered smoke/benchmark scripts outside `tests/`.
- Classify tests: unit, integration, contract, performance, benchmark.
- Enforce strict-mode invariants (no fakeredis/sqlite/kafka-python usage) via contract tests.

Actions (Completed)
- Moved `scripts/math_smoke_test.py` → `tests/smoke/math_smoke_test.py`.
- Moved `scripts/kafka_smoke_test.py` → `tests/kafka/kafka_smoke_test.py`.
- Moved `benchmarks/nulling_test.py` → `tests/benchmarks/nulling_test.py`.
- Added markers (`unit`, `contract`, `performance`, `benchmark`).
- Added `tests/conftest.py` to skip performance/benchmark by default.

Planned (Next)
- Re-tag existing files under `tests/` with appropriate markers.
- Introduce polling helper to remove fixed `sleep()` calls.
- Create contract tests for Avro schema invariants & banned keyword scan.
- Add performance smoke harness measuring p95 latency for predictor bind/unbind.

Acceptance
- `pytest -m unit` runs < 2s locally.
- No test files remain outside `tests/` besides intentional non-test runtime scripts.
- Benchmark/performance tests excluded from CI by default.
- Contract suite fails if banned libraries or non-Avro serialization reintroduced.

## Appendix — Memory Subsystem Roadmap (Strict Mode)

Date: 2025-11-11

### Goals
- No mocks, no fallbacks, no silent bypasses. External memory is required.
- Canonical env precedence and strict health/readiness semantics.
- Low-cardinality metrics and complete E2E traceability for one-message lifecycle.

### Phase 1 — Fail-Fast + Health Alignment + Metrics (Started)
- Config centralization: single source of truth for `SOMABRAIN_MEMORY_HTTP_ENDPOINT/TOKEN` via `somabrain/config.py` and `somabrain/infrastructure.py`.
- Fail-fast startup: API refuses to start without memory endpoint/token; memory client refuses calls without token.
- Watchdog: lightweight periodic check that attempts to reset the circuit breaker after backoff.
- Health alignment: `/health` exposes memory health and circuit state consistently.
- Metrics base: HTTP and memory-related counters/gauges/histograms exposed on `/metrics` via Prometheus client.

Implementation references
- `somabrain/memory_client.py`: HTTP-only client, strict token requirement, no dev fallbacks.
- `somabrain/services/memory_service.py`: circuit breaker, `_reset_circuit_if_needed()` and `_health_check()`.
- `somabrain/app.py`: startup diagnostics, watchdog task, `/health` includes `memory_circuit_open`.
- `somabrain/metrics.py`: strict dependency on `prometheus_client` (noop shim removed).
- `scripts/ci_readiness.py`: strict posture (no localhost remap fallbacks).

Acceptance criteria
- Process fails to boot if memory endpoint or token is missing.
- `/health` returns `ok=true` only when memory service is reachable; includes `memory_circuit_open=false` under steady state.
- Metrics scrape returns without exceptions; circuit breaker metric is stable at 0 during normal operation.
- Readiness script exits non-zero when Kafka/Postgres/OPA/Redis are not reachable per configured endpoints (no host remaps).

Status
- Enforced: metrics strict dependency, no pytest bypass for backend enforcement, memory token required, readiness script strict.
- Added: watchdog loop and `memory_circuit_open` in `/health`.

### Phase 2 — Service Breaker, Dual-Write (Optional), Secondary Failover (Planned)
- Service breaker reason propagation: last error type/ts surfaced in diagnostics and health response.
- Optional dual-write to Kafka audit for write intents (idempotent), disabled by default.
- Optional secondary memory endpoint (hot-warm) with controlled failover policy; off by default, requires explicit config.

Acceptance criteria
- Health includes `memory_last_failure` structure (type, ts, attempts).
- Feature flags gated; when disabled, no side-effects or extra latency.

### Phase 3 — Outbox Replayer (Planned)
- Dedicated replayer process for previously recorded outbox events (best-effort), idempotent semantics only.
- Bounded retry with jitter and batch sizing; metrics for replay outcome.

Acceptance criteria
- Replayer metrics: processed_total, success_total, retry_total, dropped_total.
- E2E replay scenario documented and test-covered.

### Phase 4 — Chaos/SLO Gates (Planned)
- Inject controlled memory outages to validate circuit transitions and health propagation.
- Define SLOs: recall p95 latency, store error budget, circuit open rate.

Acceptance criteria
- Automated chaos job produces expected circuit flip/flop traces without flapping.
- Alerting thresholds documented (Prometheus rules kept out-of-scope for now).

### Metrics Specification (Low-Cardinality)
- HTTP:
    - `somabrain_http_requests_total{method,path,status}`
    - `somabrain_http_latency_seconds{method,path}`
- Memory breaker/outbox:
    - `somabrain_memory_circuit_breaker_state` gauge (0|1)
    - `memory_http_failures_total` counter (sync with service breaker)
    - `somabrain_memory_outbox_sync_total{status}` counter
- Retrieval/store KPIs:
    - `somabrain_recall_latency_seconds{namespace}`
    - `somabrain_ann_latency_seconds{namespace}`
    - Governance gauges per tenant/namespace (items, eta, sparsity, margin)

Notes
- `somabrain/metrics.py` is the single registry; avoid duplicate registration.
- No noop metrics path allowed; prometheus_client must be present.

### Health and Readiness
- `/health` includes:
    - `components.memory` (http=true/false)
    - `memory_circuit_open` (bool)
    - `api_version`, `namespace`, plus optional constitution info
- Readiness script (`scripts/ci_readiness.py`):
    - Strict checks for Postgres/Redis/Kafka/OPA; no host-port remaps.
    - Exits 1 on any failure; prints concise reasons.

### E2E Full Trace Test
- Test path: `tests/e2e/test_full_trace_message.py`.
- Flow:
    1) POST remember
    2) Poll recall until hit
    3) Snapshot `/health`, `/diagnostics`, `/metrics`
    4) Fetch memory service `/health` and `/memories/search` responses
    5) Save all artifacts under `artifacts/`

Acceptance criteria
- Artifacts include write/read ids and timestamps; metrics scrape is present and parseable.
- Test fails when memory or infra is not ready (no silent bypass).

### Environment Policy (Canonical)
- Memory: `SOMABRAIN_MEMORY_HTTP_ENDPOINT`, `SOMABRAIN_MEMORY_HTTP_TOKEN` (required)
- Infra: `SOMABRAIN_POSTGRES_DSN`, `SOMA_KAFKA_BOOTSTRAP` (or `SOMABRAIN_KAFKA_URL`), `SOMABRAIN_OPA_URL`, `SOMABRAIN_REDIS_URL`
- Mode flags that imply bypass are disallowed; enforcement is unconditional for memory.

### Non-Goals
- No embedded in-process memory backend.
- No metrics noop or fake exporters.
- No readiness host remapping for developer convenience.

### Changelog (Phase 1 Edits)
- `somabrain/metrics.py`: removed noop shim; strict prometheus_client requirement.
- `somabrain/app.py`: removed pytest bypass; added watchdog; OPA middleware mandatory; `/health` includes `memory_circuit_open`.
- `somabrain/memory_client.py`: memory endpoint and token strictly required.
- `scripts/ci_readiness.py`: removed localhost remap fallbacks; strict checks only.
