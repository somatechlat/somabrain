# Canonical Roadmap — Cognitive Thread + Era of Experience

This single roadmap combines the existing cognitive-thread plan with the “Era of Experience” learning layer. It preserves our single canonical Docker image policy, keeps all rollout values-gated, and defines clear acceptance tests per sprint.

## 1) Architecture (high-level)

```
+-------------------+      +-------------------+      +-------------------+
|   Client/API      | ---> |   Orchestrator    | ---> |   Predictor Core   |
| (REST/gRPC)       |      | (Plan phase)      |      | (state/agent/action)|
+-------------------+      +-------------------+      +-------------------+
	   |                         |                         |
	   v                         v                         v
   +----------------+        +----------------+        +----------------+
   | reward_producer|        | segmentation   |        | integrator_hub |
   | (Kafka prod)   |        | service (HMM)  |        | (softmax, OPA, |
   +----------------+        +----------------+        |  Redis cache)  |
	   |                         |                         |
	   v                         v                         v
   +---------------------------------------------------------------+
   |                     learner_online (Bandit/RL)                |
   |  consumes: reward_event, next_event, integrator_context       |
   |  produces: config_update (temperature, weights)               |
   +---------------------------------------------------------------+
	   |                         ^                         |
	   |                         |                         |
	   +-------------------+-----+-------------------------+
				  |
				  v
			+----------------+
			|   OPA service  |
			+----------------+
```

Notes
- Transport is Kafka; OPA is HTTP (with short timeouts, optional Redis caching).
- A small configurable shadow ratio routes a fraction of frames to an evaluation path.
- Single Docker image for all services; no per-service Dockerfiles.

## 2) Contracts & Topics (Avro)

Existing
- belief_update.avsc, global_frame.avsc, segment_boundary.avsc, integrator_context.avsc

New (to be added)
- reward_event.avsc — fields for r_task, r_user, r_latency, r_safety, r_cost (typed and versioned)
- next_event.avsc — schema for next-event predictions/errors (for learner feedback)
- config_update.avsc — exploration temperature and optional per-domain weights

Canonical topics
- Inputs: cog.state.updates, cog.agent.updates, cog.action.updates
- Core: cog.global.frame, cog.segments, cog.integrator.context (optional)
- Learning: soma.reward.events, soma.next.events, soma.config.updates (names configurable)

## 3) Feature Flags (values-gated)
- ENABLE_COG_THREADS — composite enable for predictors, segmentation, integrator, orchestrator
- Per-service flags: SOMABRAIN_FF_PREDICTOR_*, SOMABRAIN_FF_COG_* (integrator/segmentation/orchestrator)
- learnerEnabled (values) — gates learner_online and the learning loop topics

## 4) Observability & SLOs
- /healthz and /metrics on all services; PodMonitors optional
- Alerts (baseline): no frames/segments, leader-switch spike, outbox p90 high
- Alerts (extended): predictor no-emit, Kafka consumer lag
- Dashboards: integrator entropy/leader switches, predictor emits, segments dwell, learning (rewards, exploration ratio, regret estimate, shadow ratio)

## 5) Single-Image Policy
- One canonical Dockerfile for all services; deployments start the appropriate entrypoints
- No per-service Dockerfiles or multi-image building/pushing

---

## 6) Sprints & Acceptance Tests

### Sprint 0 — Foundations (Done/Verify)
- Ensure existing services (predictors, segmentation, integrator, orchestrator) run with health/metrics and pass unit/integration tests
- CI: lint/type/coverage; compose E2E smoke; kind install with in-cluster topic probe
- Acceptance: green CI; topic probe sees cog.global.frame and cog.segments

### Sprint 1 — Reward Ingestion
- Add reward_event.avsc and publish via reward_producer
- Wire tests to inject reward events and validate schema registry compatibility
- Acceptance: POST/emit produces an Avro record on soma.reward.events; CI smoke validates ≥1 record

#### Sprint 1 — Recent Progress (Nov 2025)

- Implemented local infra and orchestration improvements to stabilize reward ingestion and e2e validation:
	- Canonical image now installs the in-repo `libs` package (Avro serde available at runtime).
	- Increased Kafka healthcheck tolerance in compose to avoid spurious `unhealthy` states during broker startup.
	- Added `make smoke-e2e` and `make start-servers` Makefile targets and a `scripts/e2e_smoke.sh` script to run quick POST→consume validation.
	- Verified end-to-end: POST reward → message present on `cog.reward.events` → `learner_online` emits `cog.config.updates` → `integrator_hub` applied update (observed in logs).

Next Sprint 1 steps:
- Add a CI job to run the smoke-e2e in a runner (or lightweight compose) so PRs validate the loop automatically.
- Convert smoke test to assert on `cog.config.updates` and integrator `/tau` for stricter acceptance.

### Sprint 2 — Next-Event Heads
- Finalize next_event.avsc; ensure predictors emit NextEvent with error metric (e.g., Brier loss)
- Unit tests for prediction head; metrics somabrain_predictor_*_next_total increase
- Acceptance: learner_online can consume NextEvent; predictor error gauge < 0.05 in controlled tests

### Sprint 3 — Online Learner Loop
- Add config_update.avsc; implement learner_online consuming reward_event + next_event (+ integrator context if needed)
- Publish config_update to topic; integrator hub adjusts temperature (tau) live
- Acceptance: tau (INTEGRATOR_TAU) changes within ~30s after updates; frames reflect new weights/entropy

### Sprint 4 — OPA & Shadow Traffic
- Confirm policy delivery via infra chart; document policy rollout
- Validate shadow ratio routing and ensure integrator context shadow topic behavior
- Acceptance: ~5% frames routed to shadow; OPA veto count metric increments under test policies; decision latency within SLO

### Sprint 5 — Observability & Alerts
- Extend dashboards with learning panels (rewards, exploration ratio, regret)
- Enable extended alerts in staging; tune thresholds; Kafka consumer lag alert tied to exporter
- Acceptance: dashboards populate; alerts fire in synthetic scenarios; runbook updated

### Sprint 6 — Canary & Production Rollout
- Enable flags for a subset of traffic; monitor KPIs; rollback path verified
- Targets (examples): p99 planning ≤22ms; r_task ≥0.78; exploration-induced error ≤2%; OPA veto ≤5%; regret ≤0.05
- Acceptance: all KPIs within thresholds over an agreed window; rollback documented and tested

---

## 7) Non-Goals / Constraints
- Do not introduce multiple images or per-service Dockerfiles
- Avoid runtime behavior changes without flags; everything is values-gated

## 8) Rollback Plan
Set `featureFlags.enableCogThreads` to `false` (and/or learnerEnabled=false) in Helm values; `helm upgrade` reverts to the previous behavior instantly.

---

This is the single canonical roadmap for cognitive-thread + learning-layer production rollout. It supersedes prior drafts and remains aligned with the repository’s single-image policy and CI gates.
