> :warning: This project must be designed with simplicity, elegance, and math in mind. Only truth. No mocking, no mimicking, no fake data.

# SomaBrain 3.0 — Canonical Roadmap

SomaBrain 3.0 unifies math, memory, and cognition behind a single deterministic core. The roadmap below is the canonical source for scope, sequencing, and rollout. All workstreams adhere to five principles: **simple hot paths, exact algebra, PSD salience, unified scoring, and flag-gated rollout with rollback**.

---

## Vision Snapshot

| Pillar | Outcome |
|--------|---------|
| **Composer Math Stack** | FFT-free binding/unbinding via deterministic Rademacher masks and permutations; O(D) hot path. |
| **Vectorizer & Salience** | Fused surface/deep embeddings with Frequent-Directions sketches for PSD low-rank salience. |
| **Unified Retrieval** | Single scorer combining cosine, subspace, and recency with bounded weights; observable end-to-end. |
| **Brain Architecture** | BrainState aggregate, lifecycle hooks, modular app entry, strict domain/application/infrastructure layering. |
| **Observability & Ops** | Benchmarks, dashboards, CI gates, rollout telemetry, safe feature toggles per tenant. |

All deliverables are grouped into quarter-long **Epics** with two-week **Sprints**. Parallel teams can progress within an epic once dependencies are met.

---

## Epic A – Foundations & Infrastructure (Weeks 1-6)

| Sprint | Focus | Deliverables |
|--------|-------|--------------|
| **[A0 – Dependency Cleanup](docs/sprints/Sprint_A0.md)** | Environment parity | `pyproject` sanity sweep, Docker cache tweaks, reproducible `uv` lock, unified config loader. |
| **[A1 – Architecture Baseline](docs/sprints/Sprint_A1.md)** | Layer separation | ADR: domain/application/infrastructure boundaries, skeleton `BrainState`, top-level factory wiring. |
| **[A2 – Observability Bedrock](docs/sprints/Sprint_A2.md)** | Metrics & tracing | Prometheus upgrades, log context propagation, benchmark CI pipeline (nightly + per-PR smoke). |

**Exit criteria**: Clean Architecture scaffolding merged, monitoring stack emitting baseline metrics, nightly benchmarks running.

---

## Epic B – Math & Vectorizer Modernization (Weeks 7-12)

| Sprint | Focus | Deliverables |
|--------|-------|--------------|
| **[B0 – MathService Facade](docs/sprints/Sprint_B0.md)** | Shared numerics | `MathService` interface, Composer/Vectorizer prototypes, property-based tests. |
| **[B1 – Composer Rollout](docs/sprints/Sprint_B1.md)** | Binding/unbinding | Deterministic masks & permutations, drop-in wrappers, feature flag `math.composer.v1`, benchmarks validating O(D) throughput. |
| **[B2 – Vectorizer Fusion](docs/sprints/Sprint_B2.md)** | Embedding pipeline | Hashed sparse -> JL projection, deep embed projector, fused normalization, tenant alpha/beta config. |

**Exit criteria**: Composer & Vectorizer ready behind flags, golden math tests passing, documentation of “math playbook” published in `docs/`.

---

## Epic C – Salience & Retrieval (Weeks 13-18)

| Sprint | Focus | Deliverables |
|--------|-------|--------------|
| **[C0 – FD Salience Core](docs/sprints/Sprint_C0.md)** | Low-rank sketch | Frequent-Directions sketch service, subspace versioning, per-item projection cache. |
| **[C1 – Unified Scorer](docs/sprints/Sprint_C1.md)** | Strategy + metrics | Single scorer implementation (cosine + subspace + recency), weight configuration with safe bounds, Prometheus instrumentation. |
| **[C2 – Retrieval Pipeline](docs/sprints/Sprint_C2.md)** | Orchestration | MemoryClient adapters (HTTP, mirror, outbox), pipeline orchestrator with stage-level metrics, cache warming strategy. |

**Exit criteria**: Unified scorer powering retrieval in shadow mode, salience sketch stable under load, latency targets met in benchmarks.

---

## Epic D – Brain Architecture & Execution (Weeks 19-24)

| Sprint | Focus | Deliverables |
|--------|-------|--------------|
| **[D0 – BrainState Integration](docs/sprints/Sprint_D0.md)** | State aggregation | Tenant-scoped BrainState, lifecycle hooks (init/before/after/background), dependency injection container. |
| **[D1 – App Modularization](docs/sprints/Sprint_D1.md)** | Clean entry point | Split `somabrain.app` into bootstrapping, routers, and services; enforce domain/application boundaries. |
| **[D2 – Cognitive Loop Harmonization](docs/sprints/Sprint_D2.md)** | Policy alignment | Centralize novelty/admission policies, update hippocampus/consolidation flows, document runbooks. |

**Exit criteria**: SomaBrain app serves through modular startup, all cognitive services read from BrainState, policy configs unified.

---

## Epic E – Rollout, Migration & Excellence (Weeks 25-32)

| Sprint | Focus | Deliverables |
|--------|-------|--------------|
| **[E0 – Feature Flag & Rollback](docs/sprints/Sprint_E0.md)** | Safe migration | Dynamic per-tenant toggles, rollback playbooks, migration dashboards. |
| **[E1 – Tenant Onboarding](docs/sprints/Sprint_E1.md)** | Controlled rollout | Pilot tenant conversions, feedback loop, performance regression tracking. |
| **[E2 – World-Class Benchmarking](docs/sprints/Sprint_E2.md)** | External validation | Publish benchmark suite results, author roadmap review, finalize 3.0 launch report. |

**Exit criteria**: Composer/Vectorizer/Salience/Scorer enabled for all target tenants, KPIs met, launch report signed off.

---

## Cross-Cutting Streams

- **Documentation & Enablement**: Update `DEVELOPMENT_GUIDE.md`, create subsystem READMEs, record math walkthrough videos.
- **Quality Gates**: Property tests for math, integration tests for retrieval, load tests for salience, chaos drills for rollback.
- **Security & Compliance**: Enforce non-root containers, OPA bundles, mTLS options, audit trails in MemoryClient adapters.

---

## Execution Checklist

1. Kickoff (Week 1): Align teams, assign epic leads, baseline metrics.
2. Bi-weekly roadmap reviews synchronized with sprint demos.
3. Rollout board tracks flag status, pilot tenant feedback, regression metrics.
4. Final readiness review before enabling SomaBrain 3.0 globally.

---

*Prepared by the AI-assisted development team. This document is the canonical roadmap—update in-place as progress is made.*