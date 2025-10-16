# Roadmap Canonical — Brain 3.0

Last updated: 2025-10-16

This document is the single canonical roadmap for evolving SomaBrain into Brain 3.0: a mathematically rigorous, production-grade system built on truth and elegance. NO mocking, NO bypasses, NO approximations - only pure mathematical implementation backed by Kafka, Postgres, Redis, OPA and observed by Prometheus/Grafana.

## Purpose

- Implement a mathematically pure and elegant Brain system with rigorous HRR operations
- Ensure all operations are backed by mathematical proofs and property tests
- Make durability, observability, and resilience mathematically verifiable
- Guarantee real infrastructure usage with no fallbacks or approximations

## Principles

- Mathematical Truth: All operations must be mathematically proven and verified through property tests
- Zero Approximation: No approximations, no mocks, no stubs - only pure mathematical implementations
- Strict-Real by default: Production operation uses only real services with mathematical guarantees
- Durable-first: All operations must be provably durable with mathematical certainty
- Observable: Every operation must emit metrics that prove mathematical correctness
- Idempotent: All operations must be mathematically proven to be idempotent
- Testable: Every operation must have property tests verifying mathematical correctness

## Parallel Waves (high level)

Work is organized into five parallel waves, each focusing on mathematical correctness and verification:

1. Mathematical Core
   - Pure HRR implementation with spectral guarantees
   - Density matrix operations with PSD stability
   - Mathematically proven binding/unbinding operations
   - Property tests verifying all mathematical invariants

2. Memory & Durability
   - Mathematically verified HTTP memory service
   - Provably correct outbox pattern implementation
   - Mathematically guaranteed circuit breakers
   - Property tests for durability invariants

3. Observability & Verification
   - Mathematical proof collection through metrics
   - Verification of all mathematical invariants
   - Tracing for mathematical operation flow
   - Property tests for observability guarantees

4. Resilience & Consistency
   - Mathematically proven retry strategies
   - Provably correct data consistency
   - Verified circuit breaker behavior
   - Property tests for resilience guarantees

5. Integration & Validation
   - Full mathematical verification suite
   - Integration tests proving correctness
   - CI/CD pipeline with mathematical checks
   - Documentation of all mathematical proofs

## Sprint Cadence and Duration

- Sprint length: 1 week (7 calendar days). Each sprint contains focused objectives and incremental deliverables.
- We run sprints in parallel across waves. Typical phase for initial work: 6 sprints (6 weeks) to reach a robust MVP for Brain 3.0.

## Sprint Plan (Sprint 0..5) — high level

Sprint 0 — Mathematical Foundation (0.5 week)
- Implement core HRR operations with mathematical proofs
- Set up property testing framework for mathematical verification
- Document all mathematical invariants and their proofs
- Verify spectral properties of all operations

Sprint 1 — Quantum Operations & Memory (week 1)
- Deliverables:
  - Pure implementation of quantum operations with proofs
  - Mathematically verified memory operations
  - Property tests for all quantum operations
  - Complete mathematical documentation
  - Metrics proving mathematical correctness: `quantum_ops_verified`, `memory_ops_verified`

Sprint 2 — Mathematical Infrastructure (week 2)
- Deliverables:
  - Mathematically proven durability implementations
  - Verified idempotent operations with proofs
  - Property tests for all infrastructure operations
  - Metrics proving correctness: `durability_verified`, `idempotence_verified`
  - Integration tests with mathematical verification

Sprint 3 — Verification & Health (week 3)
- Deliverables:
  - Mathematically verified circuit breakers
  - Health endpoints with mathematical guarantees
  - Complete verification suite for all operations
  - Alert rules based on mathematical invariants
  - Continuous verification of all properties

Sprint 4 — Consumers & Data Consistency (week 4)
- Deliverables:
  - Idempotent consumers for `soma.audit` and `soma.memory.ops` that persist canonical records in Postgres.
  - Consumer offset handling: commit only after durable write.
  - Migration tool to import existing JSONL journals into outbox rows (with dedupe option).

Sprint 5 — Observability, SLOs & CI (week 5)
- Deliverables:
  - OpenTelemetry trace spans for request -> produce -> consume flows.
  - SLO definitions and Grafana dashboards for p95 latency, error rate, outbox backlog, Kafka liveness.
  - Integration smoke tests run in CI pipeline or nightly job.

Ongoing Sprints (week 6+)
- Redis optimization: key strategy, TTLs, cache hit/miss metrics.
- OPA hardening and policies; fail-closed default for strict-real.
- Security: TLS for services, secret management, production config templates.

## Roadmap Addendum — Learning Brain Stability (Oct 2025)

This addendum captures the focused plan to harden the learning brain, preserve mathematical guarantees, and validate long-horizon recall behaviour. All work adheres to strict-real policies and leverages real services only.

### Objectives
- Preserve graceful recall degradation (≥70% top-1 accuracy at 5k memories) under BHDC math.
- Stabilize unified scoring, FD sketches, and density matrices with full invariant telemetry.
- Ship benchmark + dashboard tooling to continuously verify learning brain performance.

### Sprint 1 — Mathematical Foundations (1.5 weeks)
- Fix unitary-role orthogonality checks and probability metrics in `somabrain/quantum.py`.
- Harden `PermutationBinder` division semantics and expand BHDC property tests.
- Improve density matrix projection resilience and add corresponding tests/metrics.
- Extend mathematical metrics (orthogonality, conservation, binder conditioning) and update docs (`docs/architecture/math/*`).

### Sprint 2 — Unified Recall Stability (2 weeks)
- Redesign recency damping in `memory_client._rescore_and_rank_hits` with bounded age semantics surfaced via `Config`.
- Blend density-aware cleanup back into WM (`somabrain/wm.py`) and surface margin metrics.
- Tune HRR context management (`context_hrr.py`) to mitigate interference at scale.
- Upgrade learning/recall benchmarks to emit memory-count vs accuracy curves for Grafana parity; add integration tests for ≥0.7 accuracy at target load.

### Sprint 3 — Learning Brain Validation (2.5 weeks)
- Integrate end-to-end learning soak into CI/nightly (`run_learning_test.py`, cognition benches) with artifact retention.
- Expand strict-real enforcement across memory client paths and ensure no stub fallbacks during tests.
- Update Prometheus/Grafana assets with new metrics (FD health, recall vs capacity, recency clamps).
- Document configuration knobs and release guidance; validate full test suite + stress benches.

### Guiding Guardrails
- Deterministic BHDC/HRR operations with instrumentation for every invariant.
- No mock/stub fallbacks; strict-real enforcement end-to-end.
- Telemetry-first validation: dashboards must surface invariant violations before accuracy regresses.

## Parallel sprint assignments (who/what)

This repo currently is single-team developer-run. Roles map to files but are flexible:

- Core/DB Engineer: implements `outbox_events` schema, migrations, `somabrain/db/outbox.py`, migration scripts.
- Eventing Engineer: implements `outbox_publisher.py`, Kafka producer hardening, idempotence semantics.
- Resilience Engineer: circuit-breaker wrappers, retry logic, dead-letter handling.
- Observability Engineer: metrics completion, dashboards, alerts, tracing.
- QA/CI Engineer: tests, smoke scripts, CI pipeline integration.

If you want, I can add TODO items into the repo and assign tickets. For now the roadmap suffices as canonical.

## Strict-Real Mode and Fallback Policy

- Flag: `ALLOW_JOURNAL_FALLBACK` (default: `0` in production). When `0` the system must not write to JSONL journal automatically.
- Behaviour:
  - If `ALLOW_JOURNAL_FALLBACK=0`, writes that cannot be enqueued to outbox or successfully published must return an explicit error (and increment metrics). Operator must enable fallback to allow auto-journal writes.
  - If `ALLOW_JOURNAL_FALLBACK=1`, journaling is allowed (for local recovery), and those actions must be visible via `somabrain_audit_journal_fallback_total` metric.

## Mathematical Verification Metrics

- Quantum Operation Metrics:
  - `quantum_hrr_spectral_property` (gauge): Verify |H_k|≈1 for all operations
  - `quantum_binding_accuracy` (histogram): Measure binding/unbinding roundtrip accuracy
  - `quantum_role_orthogonality` (gauge): Verify role vector orthogonality
  - `density_matrix_trace` (gauge): Verify |tr(ρ) - 1| < 1e-4

- Mathematical Guarantees:
  - `math_invariant_verified_total{operation}` (counter): Track mathematical verification
  - `property_test_passed_total{test}` (counter): Track property test success
  - `mathematical_proof_verified{proof}` (gauge): Track proof verification

- Implementation Verification:
  - `operation_mathematical_correctness{op}` (gauge): Verify operation correctness
  - `implementation_truth_verified{component}` (gauge): Verify pure implementation
  - `mathematical_guarantee_maintained{guarantee}` (gauge): Track guarantee maintenance

- Exporter & infra alerts:
  - `kafka_exporter` reports broker health; alert if broker_up == 0.
  - `postgres_exporter` reports DB state; alert on high commit latency or failing checks.
  - `redis` metrics: evictions, memory usage.

## Migration plan (journal -> outbox)

1. Add a migration script `scripts/journal_to_outbox.py` that:
   - Reads JSONL journal files and inserts deduplicated rows into `outbox_events` with `created_at` timestamps.
   - Optionally mark old journal lines as archived (move file). Run in operator window.
2. Run tool in a controlled environment; verify outbox pending counts and run publisher until backlog cleared.
3. Decommission journal auto-fallback once backlog = 0 and metrics stable.

## Testing & CI

- Unit tests: for outbox enqueue logic, publisher idempotence, circuit-breaker open/close semantics.
- Integration smoke test (docker-compose): bring up Kafka/Postgres/Redis/OPA/app -> POST audit event -> assert outbox row -> run publisher -> assert Kafka topic -> run consumer -> assert DB record.
- CI: add unit test stage for PRs; optional integration stage nightly or on-demand.

## Runbook — daily operations (short)

1. If `outbox_pending` grows: check `outbox_publisher` logs, restart worker if needed, inspect `outbox_events.last_error`.
2. If `somabrain_audit_journal_fallback_total` increases: check if `ALLOW_JOURNAL_FALLBACK` is set; otherwise investigate Kafka connectivity and DB availability.
3. If circuit-breaker opens: check target service health (memory HTTP, Kafka) and recent error rates.

## Risks and mitigation

- Risk: Outbox backlog growth if publisher fails. Mitigation: alerting and operator replay script + dead-letter policy.
- Risk: Delays because enqueuing is sync to DB. Mitigation: keep payload small, tune DB, use batching in publisher.
- Risk: Duplicate events. Mitigation: dedupe keys and idempotent consumer writes.

## Mathematical Acceptance Criteria

1. All quantum operations are mathematically proven correct with property tests:
   - HRR operations maintain spectral properties (|H_k|≈1)
   - Binding/unbinding operations are provably invertible
   - Density matrix maintains PSD property

2. All implementations are purely mathematical with no approximations:
   - No mocks or stubs anywhere in the codebase
   - All operations have mathematical proofs
   - All guarantees are verified through property tests

3. All mathematical invariants are continuously verified:
   - Continuous property test execution
   - Real-time mathematical verification metrics
   - Automated proof verification

4. Complete mathematical documentation exists:
   - Formal proofs for all operations
   - Mathematical specifications for all components
   - Verification procedures for all guarantees

5. Integration tests verify mathematical correctness end-to-end

## Immediate next steps (today)

1. Confirm you want me to start implementing Sprint 1 (Transactional Outbox). I will then:
   - Add Alembic migration and `somabrain/db/outbox.py` skeleton.
   - Update `somabrain/audit.py` to use outbox enqueue in strict-real.
   - Add unit tests for outbox enqueue semantics.
2. If confirmed I will create the PR/patch set and run tests locally.

---

If you want changes to this canonical roadmap (timelines, more granular tasks, added constraints), say so and I will update this file immediately. If you want me to start implementing Sprint 1 now, confirm and I’ll begin. 
