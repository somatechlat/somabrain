# SomaBrain Architecture Assessment — AROMADP Strict-Mode

Date: 2025-11-09

## Overview

SomaBrain is an event-driven, microservices-aligned system centered on a cognitive integrator and predictor threads. Core transports use Kafka with Avro schemas; Redis supports working memory; Postgres stores config/metadata; OPA governs policy; Prometheus exposes metrics; tracing is provisioned via an observability provider. The AROMADP mandate removes all mocks/fallbacks/disable paths and enforces real infrastructure and Avro-only serialization where schemas exist.

## Topology & Responsibilities

- Client/API: REST/gRPC entrypoints under `somabrain/api` and `somabrain/app.py`.
- Predictor Threads: `services/predictor-{state,agent,action}` publish belief updates with confidence and delta_error.
- Integrator Hub: `somabrain/services/integrator_hub.py` consumes belief updates, computes leader via softmax or normalized fusion, emits `global_frame`, and SOMA compatibility context. Integrates OPA gating and drift monitoring.
- Learning/Calibration: `somabrain/services/calibration_service.py` enforces ECE improvements; future learner loops consume rewards and emit `config_update`.
- Drift Monitoring: `somabrain/monitoring/drift_detector.py` aggregates entropy/regret and emits drift events, optionally triggering rollback.
- Observability: Metrics under `somabrain/metrics`, alerts in `alerts.yml`, dashboards Provisioned via Prometheus/Grafana folders.
- Orchestration: Docker Compose and Makefile manage Kafka, Schema Registry, Redis, Postgres, OPA, Prometheus.

## Transports & Contracts

- Kafka topics (defined in `somabrain/common/kafka.py` and Roadmap):
  - Inputs: `cog.state.updates`, `cog.agent.updates`, `cog.action.updates`
  - Core: `cog.global.frame`, `cog.segments`, `soma.integrator.context`
  - Learning: `cog.reward.events`, `cog.next.events`, `cog.config.updates`
  - Telemetry: `cog.fusion.drift.events`, `cog.predictor.calibration`
- Avro Schemas: `proto/cog/*.avsc` including `belief_update`, `global_frame`, `next_event`, `reward_event`, `config_update`, `segment_boundary`, `integrator_context`, `fusion_drift_event`.
- Serde: `libs.kafka_cog` Avro helpers; current code still allows JSON fallback in multiple paths.

## Stores & Policy

- Redis: working memory cache (`somabrain/common/utils/cache` usage in integrator).
- Postgres: configured via `SOMABRAIN_POSTGRES_DSN` in compose; used by storage modules under `somabrain/storage`.
- OPA: `somabrain_opa` container; integrator calls policy endpoint with fail-open configurable; alerts for veto ratio.

## Observability

- Prometheus metrics: latency histograms, integrator counters/gauges, alpha metrics, entropy, κ, segmentation KPIs, calibration ECE. Alerts added for drift, normalization disable, calibration drift, κ low, Kafka lag, OPA veto ratio.
- Tracing: predictor services initialize tracing via `observability.provider`; integrator uses a no-op fallback when provider missing (to be removed).

## Duplication & Inconsistencies (Hotspots)

- Producer/serde duplication across services; local JSON fallback per service.
- Feature flag handling duplicated and permissive (e.g., predictor mains allow disabling core services).
- Optional imports with silent None fallbacks (`KafkaProducer`, metrics, Avro serde).
- OPA fail-open may violate strict-mode intent.
- Legacy tests formerly used `SOMABRAIN_DISABLE_KAFKA`; this flag has been removed. Strict mode permits only real Kafka, with optional test bypass via `SOMABRAIN_REQUIRE_INFRA=0` when explicitly set for unit isolation.

## Anti-Fallback Audit (sample findings)

- `somabrain/common/kafka.py`: disable flag pathway removed; Kafka mandatory; JSON fallback eliminated for Avro-backed topics.
- `integrator_hub.py`: Avro→JSON fallback for decode/encode; OPA fail-open path; optional Redis; no-op tracer fallback.
- `drift_detector.py`: optional Kafka imports; producer optional; toggles features via env on rollback.
- `calibration_service.py`: metrics optional; producer optional; prints when disabled by flag.

## Centralization & De-dup Plan

1) Messaging Core
- Enforce Kafka mandatory: remove `SOMABRAIN_DISABLE_KAFKA`; on missing brokers, raise at startup.
- Avro-only where schema exists: drop JSON fallback for `belief_update`, `global_frame`, `next_event`, `reward_event`, `config_update`, `integrator_context`, `fusion_drift_event`.
- Single factory: `somabrain/common/kafka.py` exposes `producer()`, `consumer()`, `serde(schema)` with health checks and schema cache.

2) Event Builders
- `somabrain/common/events.py`: extend with regret computation, attribution γ_d, λ_d fields; shared NextEvent/ConfigUpdate builders.

3) Observability
- `somabrain/common/observability.py`: mandatory tracing init and metrics registry; remove all no-op fallbacks; fail startup if provider missing.

4) Entry & Boot
- `services/entry.py`: unified entry dispatcher; remove per-service `_bootstrap` duplication; standard health server and metrics endpoint.

5) Policy & Security
- OPA fail-closed default; decision latency histogram; circuit breaker metric; alert on p99 > SLO.
- Auth always-on: remove disable paths, ensure all routes include auth dependencies.

6) Data Layers
- Redis mandatory for memory subsystems; remove fakeredis/local WM fallbacks.
- Postgres mandatory; eliminate SQLite/in-memory fallbacks; migration gate before start.

## Architecture Patterns

- Hexagonal ports/adapters: define clear ports for messaging, cache, db, policy; implement adapters in `somabrain/common`.
- Event-first contracts: Avro schemas are single source of truth; codegen where possible; strict compatibility checks in CI.
- Idempotent producers/consumers with health gating: verify topic metadata before consuming; unify error handling and backoff.
- Telemetry by default: spans around IO, histograms for latencies, counters for decisions and rollbacks.

## Migration Plan (Strict Mode)

Phase 1: Kafka & Tests
- Remove disable flags; make producers/consumers mandatory.
- Convert drift/calibration tests to integration against Kafka (compose profile for CI and local).

Phase 2: Serde & Contracts
- Remove JSON fallbacks on Avro-backed topics; add Avro round-trip tests; fail on schema/serde errors.

Phase 3: Observability & Policy
- Remove no-op tracer/metrics; enforce tracing provider; OPA fail-closed and alerting.

Phase 4: Data Layers
- Enforce Redis/Postgres connectivity at boot with health checks; remove local fallbacks.

Phase 5: Consolidation
- Introduce `services/entry.py`; refactor predictors/integrator to import shared factories/builders; target ≥20% CLoC reduction in service mains.

## Acceptance Criteria

- Invariant audit test finds zero banned keywords: disable, fallback, fakeredis, noop tracer.
- All e2e/integration tests use real infra; compose health-gated.
- Avro-only for covered topics; JSON path deleted.
- OPA fail-closed active; auth enforced on all routes.
- Observability dashboards show α, entropy, κ, ECE, drift rates.
- Predictor mains CLoC reduced ≥20%; duplication eliminated.

## Risks & Mitigations

- Infra startup flakiness: compose health checks + bounded retries; fast fail on missing deps.
- Latency overhead from instrumentation: sample spans where needed; keep metrics full.
- Developer friction: one-command `make dev` brings full stack; docs updated.

## Immediate Actions (Proposed Diffs)

- `somabrain/common/kafka.py`: remove `SOMABRAIN_DISABLE_KAFKA` handling; raise if KafkaProducer unavailable; add `consumer()` and schema-registry health probe.
- `somabrain/services/integrator_hub.py`: delete JSON fallbacks where Avro exists; replace no-op tracer with hard requirement; enforce OPA fail-closed; require Redis URL.
- `somabrain/monitoring/drift_detector.py`: make producer required when enabled; remove optional kafka import path; stop env-based feature toggles on rollback, emit only events.
- `somabrain/services/calibration_service.py`: require metrics and producer; remove disabled prints; gate solely by `ENABLE_CALIBRATION`.
- Tests: replace `SOMABRAIN_DISABLE_KAFKA` with integration fixtures using compose services; add Avro round-trip tests for all topics.

---

This assessment reflects a full code sweep and aligns concrete refactors with AROMADP to centralize, de-duplicate, and enforce strict-mode invariants across transports, contracts, observability, and policy.
