> :warning: SomaBrain 3.0 must stay mathematically exact on the hot path. All upgrades preserve deterministic Composer binding, PSD salience, and flag-gated rollout.

# SomaBrain 3.0 — Refactored Roadmap (2025 Q4)

This roadmap merges the latest architectural analysis (tunable math surfaces, cognition benchmark gaps, optional micro-preconditioner) with launch execution. Work is organized into **lanes** that can run in parallel once dependencies are satisfied. Each sprint is two weeks.

---

## Vision Snapshot

| Pillar | 3.0 Outcome |
|--------|-------------|
| **Immutable Math Core** | Composer bind/unbind (O(D)), FD salience sketch, Unified scorer; exact and auditable. |
| **Tunable Surfaces** | Fusion, cue strengths, scorer weights, FD rank, diversification gate; per-tenant knobs with EMA + clamps. |
| **Adaptive Learning Loop** | Optional Q/W micro-preconditioner trained on clicks; gradient updates out of band with safe rollback. |
| **Observability & Ops** | Precision/latency dashboards, FD energy health, cue confidence, gradient drift alerts, benchmark CI. |
| **Tenant Isolation & Safety** | Feature flags, checkpoint governance, per-tenant BrainState, A/B rollout with reversible defaults. |

---

## Lane Overview

| Lane | Objective | Dependencies | Parallelization |
|------|-----------|--------------|-----------------|
| **Lane α – Core Hardening** | Finish math invariants, cognition/RAG regression fixes. | Existing Composer/FD/scorer shipped. | Blocks others only where noted. |
| **Lane β – Tunable Surfaces** | Operationalize fusion, cue, scorer, FD auto-rank knobs per tenant. | Lane α baseline. | Can start once α.1 completes. |
| **Lane γ – Adaptive Learning Loop** | Introduce Q/W preconditioner, gradient trainer, checkpoint ops. | Lanes α, β instrumentation. | Starts after α.2 + β.1. |
| **Lane δ – Observability & Governance** | Metrics, alerts, data governance, benchmark automation. | α.1 | Runs parallel with β, γ. |
| **Lane ε – Rollout & Launch** | Benchmarks, launch report, comms, tenant rollout. | α–δ deliverables. | Sequenced near end. |

---

## Lane α – Core Hardening (Weeks 1-4)

| Sprint | Focus | Key Deliverables | Notes |
|--------|-------|------------------|-------|
| **α.1 – Cognition Benchmark Rehab** | Resolve Gate2 (k=1) precision drop and Gate3 latency warn. | Parameter sweeps for cue γ and scorer weights; rerun `cognition_core_bench.py`; publish PASS gating checklist. | Enables β lane. |
| **α.2 – RAG Benchmark Restoration** | Fix retriever auth/backfill, re-run `rag_bench.py` with hit-rate targets. | Auth tokens or stub toggles, rerun with SOMABRAIN_STRICT_REAL_BYPASS=0, capture latency/hit improvements. | Must complete before γ and ε. |
| **α.3 – Stress & Numerics Sign-off** | Confirm `run_stress.py` and numerics suite under new parameters. | Annotated `results_stress.json`, unitary numerics delta documentation, alert thresholds confirmed. | Parallel with β.1 once α.1 done. |

---

## Lane β – Tunable Surfaces (Weeks 3-8)

| Sprint | Focus | Key Deliverables | Parallel |
|--------|-------|------------------|----------|
| **β.1 – Tenant Config Surfaces** | Expose fusion α/β, cue γ, scorer weights, half-life, FD rank in config + BrainState. | Config schema, clamps, audit logging; tenant defaults from research doc. | Parallel with α.3, δ lane. |
| **β.2 – Adaptive Rules & Auto-Rank** | Implement FD energy ratio monitoring with rank bump rule; diversification gate logic. | Energy ratio metrics + alerts; diversification gate with η control + tests. | Parallel with δ.2. |
| **β.3 – Pattern Completion & Fast Path** | Cue confidence metric, fast-path promotion rules, A/B hooks. | Confidence calculation spec, gating thresholds, unit tests. | Requires δ.1 telemetry. |

---

## Lane γ – Adaptive Learning Loop (Weeks 7-12)

| Sprint | Focus | Key Deliverables | Dependencies |
|--------|-------|------------------|--------------|
| **γ.0 – Data Plumbing** | Capture query-positive-negative tuples, tenant tags, click signals. | Retrieval event bus, PII-safe storage, replay harness. | α.2, β.1, δ.1 |
| **γ.1 – Trainer Architecture** | Householder-based Q, diagonal(+low-rank) W, InfoNCE/hinge trainer, regularizers, checkpoint writer. | Trainer design doc, unit tests for orthogonality, config clamps. | Requires γ.0. |
| **γ.2 – Inference Integration** | Load checkpoints, apply Q/W before Composer, inverse for unbind path, flag `retrieval.preconditioner.v1`. | Hot path adapter, health checks, fallback-to-identity flow. | After γ.1 + β.2. |
| **γ.3 – Guardrails & Rollback** | Drift detection (`||Q-I||`, `||W^{-1}||`), precision delta alerts, automated rollback. | Alert wiring, runbook updates, test rollback drills. | Parallel with δ.3. |

---

## Lane δ – Observability & Governance (Weeks 3-12)

| Sprint | Focus | Key Deliverables |
|--------|-------|------------------|
| **δ.1 – Metrics Baseline** | Prometheus exporters for precision@{1,3,5}, latency p95/p99, FD energy ratio, cue confidence, weight saturation, NaN/Inf counts. |
| **δ.2 – Gradient Telemetry** | Loss trending, checkpoint hashes, EMA vs gradient deltas, per-tenant drift dashboards. |
| **δ.3 – Benchmark Automation** | Nightly cognition, RAG, stress runs; artifact upload; alert on regression >5%. |
| **δ.4 – Governance & Compliance** | Checkpoint signing, feature flag governance, audit trail for parameter updates, data retention policy. |

Lane δ sprints can overlap with β and γ as soon as α.1 completes.

---

## Lane ε – Rollout & Launch Readiness (Weeks 11-16)

| Sprint | Focus | Exit Criteria |
|--------|-------|---------------|
| **ε.1 – Benchmark Synthesis** | Aggregate numerics, cognition, RAG, stress results with Q/W off and on; finalize charts. |
| **ε.2 – Launch Report & Comms** | Produce SomaBrain 3.0 launch report, customer brief, internal comms; document mitigation for any residual warnings. |
| **ε.3 – Tenant Pilot & A/B** | Enable `math.composer.v1`, `salience.fd.sketch`, `scorer.unified`, `retrieval.preconditioner.v1` for pilot tenants; ensure precision ≥ baseline or latency ≤60 ms p95. |
| **ε.4 – Global Readiness Review** | Steering committee sign-off, rollback drills complete, roadmap archived. |

ε.1 requires α–γ data closed; ε.3 waits for γ.3 safeguards and δ.4 governance.

---

## Cross-Cutting Streams

- **Documentation & Enablement**: Update math playbook, sprint logs, developer guides; add gradient training FAQ.
- **Quality Gates**: Property tests for math core, retrieval integration tests, regression tests for Q/W identity fallback, chaos drills for feature flag rollback.
- **Security & Compliance**: Non-root containers, OPA bundles, checkpoint audit logging, per-tenant data isolation in gradient store.

---

## Execution Checklist

1. Kickoff (Week 1): align lane leads, confirm cognition Gate2/3 + RAG auth issues.
2. Week 2 review: ensure Lane α progress unblocks β, δ.1.
3. Bi-weekly lane syncs manage cross-dependencies (β ↔ γ ↔ δ).
4. Pre-ε entry gate: alerts green, benchmarks PASS, Q/W flag ready.
5. Final readiness: complete Sprint ε.4, archive roadmap, seed 3.1 backlog.

---

*Prepared by GitHub Copilot. This is the canonical roadmap; update in place as execution progresses.*