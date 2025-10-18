# Roadmap Canonical — Brain 3.0

**Purpose**: Canonical plan for evolving SomaBrain into Brain 3.0 while preserving mathematical rigour and backend-enforced execution.

**Audience**: Product leads, roadmap owners, and engineers aligning long-term workstreams.

**Last Updated**: 2025-10-16

---

## Mission

- Implement a mathematically pure, elegant brain with rigorous HRR operations.
- Ensure every operation is backed by proofs, property tests, and real infrastructure.
- Guarantee durability, observability, and resilience with verifiable evidence.
- Eliminate mocks, stubs, and approximations—backend-enforced throughout.

## Principles

- **Mathematical truth**: Every algorithm is proven and property-tested.
- **Zero approximation**: Pure implementations only; no mock fallbacks.
- **Strict-real default**: Production and CI run with real dependencies.
- **Durable-first**: Persistence paths must have mathematical guarantees.
- **Observable**: Metrics must prove invariant adherence.
- **Idempotent**: Operations require mathematical proofs of idempotency.
- **Testable**: Property tests enforce correctness continuously.

## Parallel Waves

1. **Mathematical Core**
   - Pure HRR with spectral guarantees.
   - Density matrix operations ensuring PSD stability.
   - Binding/unbinding operations proven invertible.
   - Property tests covering invariants.
2. **Memory & Durability**
   - Verified HTTP memory service.
   - Provably correct outbox pattern implementation.
   - Mathematically guaranteed circuit breakers.
   - Property tests for durability.
3. **Observability & Verification**
   - Metrics that prove mathematical invariants.
   - Tracing for cognitive operation flow.
   - Property tests for observability.
4. **Resilience & Consistency**
   - Proven retry strategies and circuit breakers.
   - Consistency guarantees with mathematical backing.
   - Property tests for resilience.
5. **Integration & Validation**
   - End-to-end verification suite.
   - Integration tests proving correctness.
   - CI/CD pipeline with mathematical checks.
   - Documentation of proofs.

## Sprint Cadence

- One-week sprints (7 days).
- Five sprints to reach Brain 3.0 MVP, running waves in parallel.

### Sprint 0 — Mathematical Foundation (0.5 week)
- Implement HRR operations with proofs.
- Establish property testing framework.
- Document invariants and proofs.
- Verify spectral properties.

### Sprint 1 — Quantum Operations & Memory (Week 1)
- Deliver pure quantum operations with proofs.
- Harden memory operations with property tests.
- Emit metrics: `quantum_ops_verified`, `memory_ops_verified`.

### Sprint 2 — Mathematical Infrastructure (Week 2)
- Ship durable HTTP memory service.
- Implement idempotent operations.
- Add integration tests with mathematical verification.
- Emit metrics: `durability_verified`, `idempotence_verified`.

### Sprint 3 — Verification & Health (Week 3)
- Verify circuit breakers and health endpoints.
- Add alert rules for invariants.
- Continuous verification across components.

### Sprint 4 — Consumers & Consistency (Week 4)
- Implement idempotent Kafka consumers for audit pipelines.
- Manage offsets post-durable write.
- Provide JSONL-to-outbox migration tooling.

### Sprint 5 — Observability, SLOs & CI (Week 5)
- Add OpenTelemetry spans for end-to-end flows.
- Define SLOs and dashboards (p95 latency, error rate, backlog).
- Integrate smoke tests into CI/nightly runs.

### Ongoing (Week 6+)
- Redis optimisation: key strategy, TTLs, hit/miss metrics.
- OPA hardening with fail-closed defaults.
- Security: TLS, secrets, production configs.

---

## Roadmap Addendum — Learning Brain Stability (Oct 2025)

Objectives:
- Maintain ≥70% top-1 accuracy at 5k memories under BHDC math.
- Stabilise unified scoring, FD sketches, and density matrices with telemetry.
- Provide benchmarks and dashboards to verify learning performance continuously.

### Sprint 1 — Mathematical Foundations (1.5 weeks)
- Fix unitary-role orthogonality checks in `somabrain/quantum.py`.
- Harden `PermutationBinder` division semantics; expand BHDC property tests.
- Improve density matrix projection resilience and metrics.
- Extend metrics (orthogonality, conservation, binder conditioning) and update docs.

### Sprint 2 — Unified Recall Stability (2 weeks)
- Redesign recency damping in `memory_client._rescore_and_rank_hits`.
- Reinstate density-aware cleanup in working memory and surface margin metrics.
- Tune HRR context management to minimise interference.
- Upgrade learning benchmarks to emit capacity vs. accuracy curves.

### Sprint 3 — Learning Brain Validation (2.5 weeks)
- Integrate end-to-end learning soak into CI/nightly runs (`run_learning_test.py`).
- Enforce backend-enforced across memory client paths in tests.
- Update Prometheus/Grafana assets with new metrics (FD health, capacity curves).
- Document knobs and release guidance; run full stress suite.

### Guardrails
- Deterministic BHDC/HRR operations with instrumentation for every invariant.
- No mock or stub fallbacks; backend-enforced enforcement end-to-end.
- Telemetry-first validation with dashboards surfacing violations before regressions.

---

## Roles & Ownership

- **Core/DB Engineer**: `outbox_events` schema, migrations, `somabrain/db/outbox.py`.
- **Eventing Engineer**: `outbox_publisher.py`, Kafka producer hardening, idempotence.
- **Resilience Engineer**: Circuit breakers, retry logic, dead-letter handling.
- **Observability Engineer**: Metrics, dashboards, alerts, tracing.
- **QA/CI Engineer**: Tests, smoke scripts, CI integration.

---

## Strict-Real Policy

- `ALLOW_JOURNAL_FALLBACK` defaults to `0`. When disabled, failed writes return errors instead of journalling.
- When enabled (`1`), journalling increments `somabrain_audit_journal_fallback_total` and is visible to operators.

---

## Mathematical Verification Metrics

- `quantum_hrr_spectral_property` (gauge) — |Hₖ| ≈ 1 for all operations.
- `quantum_binding_accuracy` (histogram) — Bind/unbind roundtrip accuracy.
- `quantum_role_orthogonality` (gauge) — Role vector orthogonality.
- `density_matrix_trace` (gauge) — |trace(ρ) - 1| < 1e-4.
- `math_invariant_verified_total{operation}` — Property test coverage.
- `property_test_passed_total{test}` — Property test success counts.
- `mathematical_guarantee_maintained{guarantee}` — Guarantee tracking.
- Exporter metrics (`kafka_exporter`, `postgres_exporter`, Redis telemetry) cover infra health.

---

## Outbox Migration Plan

1. Build `scripts/journal_to_outbox.py` to import JSONL journals into `outbox_events` with dedupe.
2. Run tool in maintenance window; ensure backlog drains and publishers recover.
3. Decommission journal fallback once backlog hits zero.

---

## Testing & CI Requirements

- Unit tests: outbox enqueue logic, publisher idempotence, circuit-breaker semantics.
- Integration smoke: docker-compose stack → POST audit event → verify outbox → publish to Kafka → consume into Postgres.
- CI gates: property tests, integration tests (nightly), benchmarks as artefacts.

---

## Daily Operations Snapshot

1. Monitor `outbox_pending`; restart publishers or investigate DB if backlog grows.
2. Investigate increases in `somabrain_audit_journal_fallback_total`—they indicate dependency failures.
3. When circuit-breakers open, inspect target service health and recent error rates.

---

## Risks & Mitigations

| Risk | Mitigation |
| --- | --- |
| Outbox backlog growth | Alerting + replay scripts and dead-letter policy |
| Enqueue latency | Keep payloads small, tune DB, use publisher batching |
| Duplicate events | Dedupe keys and enforce idempotent consumers |

---

## Mathematical Acceptance Criteria

1. HRR operations maintain spectral properties; property tests validate determinism and orthogonality.
2. Implementations remain pure mathematics—no approximations, mocks, or stubs.
3. Invariants are continuously verified via metrics and property tests.
4. Documentation includes formal proofs and verification procedures.
5. Integration tests demonstrate mathematical correctness end-to-end.

---

## Immediate Next Steps

1. Confirm go-ahead for Sprint 1 (Transactional Outbox):
   - Add Alembic migration and `somabrain/db/outbox.py` skeleton.
   - Update `somabrain/audit.py` to enqueue into the outbox under backend-enforced.
   - Add unit tests for outbox enqueue semantics.
2. Once confirmed, prepare PRs and run the full backend-enforced test suite locally.

---

**Verification**: Roadmap stays authoritative when updated alongside implementation PRs.

**References**:
- [Technical Manual](../../technical-manual/index.md) for deployment details.
- [Development Manual](../../development-manual/index.md) for contribution workflow.
- [Changelog](../../changelog.md) for release history.
