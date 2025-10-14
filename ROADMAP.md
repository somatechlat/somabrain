# SomaBrain "Faster ⇒ Smarter" Canonical Roadmap (Q4 2025 – Q1 2026)

> **Principle:** More cycles, cleaner signals, richer context, preemptive control. Every lane drives binary/sparse hypervectors, FD salience, procedural/episodic context, and proactive meta-optimization. FFT-era math, dense ρ, and reactive-only adaptation are removed.

---

## Vision Pillars

| Pillar | Target Outcome |
| --- | --- |
| **BHDC Memory Core** | Binary/sparse hypervectors, permutation binder, optional Walsh–Hadamard mix, FD salience sketch (rank r ≪ D). |
| **Unified Scoring** | Single O(D + r) scorer combining cosine, subspace projection, and recency decay with bounded weights. |
| **Proactive Learning Engine** | Reactive dopamine EMA retained as fallback, wrapped by meta predictor g(m) for preemptive θ updates. |
| **Context Expansion** | Procedural program vectors (permutation^t encodings) and episodic causal log powering targeted corrections. |
| **Observability & Safety** | Dashboards for drift, FD energy capture, superposition load K, meta confidence; hard clamps and rollback gates. |

Flags (off → on sequence): `binding_method={mask,bhdc}`, `salience_method={dense,fd}`, `learning_mode={reactive,proactive}`, `context_layers={associative,procedural,episodic}`.

---

## Lane Overview

| Lane | Focus | Notes |
| --- | --- | --- |
| **A – Memory Core Rewrite** | BHDC encoder, permutation binder, FD salience, unified scorer. | Blocks downstream lanes. |
| **B – Context Systems** | Procedural program vectors + episodic causal log. | Starts after A.2 metrics available. |
| **C – Meta Learning Engine** | Stress metric pipeline, predictor g(m), proactive θ planner. | Needs A telemetry + B signals. |
| **D – Observability & Safety** | Metrics, dashboards, feature flag governance, rollout gates. | Runs parallel to A once BHDC API defined. |
| **E – Rollout & Readiness** | Benchmarks, canaries, documentation, tenant migration. | Final lane.

---

## Lane A – Memory Core Rewrite (Weeks 1-6)

| Sprint | Objective | Deliverables | Gates |
| --- | --- | --- | --- |
| **A.1 BHDC Foundations** | Introduce binary/sparse hypervector encoder and `PermutationBinder`. Remove mask composer. | `somabrain/math/bhdc_encoder.py`, `PermutationBinder`, deterministic seeding, unit tests, feature flag `binding_method`. | Round-trip bind/unbind ≥ 0.98 cosine; sparsity target within ±1%. |
| **A.2 Salience Sketch (FD)** | Live FD sketch `S diag(α) Sᵀ`, online updates O(D r). | FD module, shrink step validation, PSD + trace normalization tests, energy capture metric. | FD energy ≥ 0.9 vs dense baseline on replay log. |
| **A.3 Unified Scorer** | O(D + r) scorer combining cosine, FD projection, recency. | Scorer refactor, bounded weights in config/Redis, telemetry for weight saturation, regression suite. | Precision@3 ≥ baseline; p95 latency ≤ baseline. |
| **A.4 Legacy Purge & ADR** | Remove FFT/mask code, update ADRs, ensure CI red if legacy path invoked. | Deleted modules, ADR-003 BHDC, migration notes, property tests. | No legacy imports in repo; CI clean. |

**A – Benchmark Validation Snapshot (in scope for A.4 sign-off)**
- Latency & throughput: permutation binding and unified scorer outpace FFT/Wiener pipelines; FD ρ lets us score full candidate sets faster than dense ρ (see `plot_binding_throughput.png`, `plot_scoring_timing.png`, `plot_salience_timing.png`).
- Quality: retain FFT-HRR for high-K superposition behind feature flags; permutation path meets accuracy for low-K workloads (`plot_binding_robustness.png`).
- Salience sketch: FD rank captures high spectral energy with low relative error; adjust per-tenant rank when dashboards flag drops (`plot_fd_quality.png`).
- Learning: proactive meta-learning recovers quicker post environment shifts versus reactive-only, with bounded-rate + confidence gating fallbacks (`plot_learning_curves.png`).

---

## Lane B – Context Systems (Weeks 4-10)

| Sprint | Objective | Deliverables | Gates |
| --- | --- | --- | --- |
| **B.1 Procedural Encoding** | Program vector `P = ⊙ Π^t(s_t)` with unroller. | `ProceduralProgram` API, permutation^t helper, round-trip tests ≥0.95 cosine. | Procedural flag off by default behind `context_layers`. |
| **B.2 Episodic Causal Log** | Append-only causal tuples feeding Δ signals. | Schema, storage, query API, retention policy, targeted δ emission. | Privacy review; log latency ≤ 20 ms. |
| **B.3 Context Fusion** | Combine associative, procedural, episodic cues in retrieval. | Fusion weights surfaces, cleanup integration, benchmarks on workflow tasks. | Success-rate ↑ vs baseline by ≥15%; rework ↓ ≥25%. |

---

## Lane C – Proactive Meta Learning (Weeks 7-12)

| Sprint | Objective | Deliverables | Gates |
| --- | --- | --- | --- |
| **C.1 Metric Bus** | Collect stress metrics m = {K, drift, p95 latency, CTR, miss@k}. | Streaming collector, normalization, tenant tagging. | Data quality checks, coverage ≥ 95% requests. |
| **C.2 Predictor g(m)** | Train tiny MLP/linear monotone model for θ*. | Offline trainer, monotonic constraints, confidence estimator, evaluation harness. | Regret reduction ≥10% on replay; confidence calibration ECE < 0.05. |
| **C.3 Runtime Planner** | Apply proactive θ adjustments with clamps + fallback. | Runtime service, guardrails, rollback to reactive when confidence low. | No divergence in canary; drift spikes ↓; p95 stable. |

---

## Lane D – Observability, Safety & Governance (Weeks 2-12)

| Sprint | Objective | Deliverables |
| --- | --- | --- |
| **D.1 Metrics Baseline** | Prometheus exporters for precision@k, K, FD energy capture, drift ratio, meta confidence. |
| **D.2 Dashboards & Alerts** | Grafana Memory Universe dashboards, alert policies (drift, energy < 0.85, meta confidence failures). |
| **D.3 Feature Flag Governance** | Flag hierarchy, rollout checklists, automated rollback pipeline, audit logs. |
| **D.4 Chaos & Compliance** | Rollback drills, checkpoint signing, data-retention updates, security review of episodic log. |

---

## Lane E – Rollout & Readiness (Weeks 11-16)

| Sprint | Objective | Exit Criteria |
| --- | --- | --- |
| **E.1 Benchmark Gauntlet** | Run BHDC, FD, meta stack across cognition/RAG/stress suites nightly. | No regression >3%; artifacts archived. |
| **E.2 Canary & Pilot** | Enable flags for pilot tenants with guardrails. | Precision ≥ baseline, latency ≤ baseline, anomaly alerts green for 7 days. |
| **E.3 Global Launch** | Docs, training, comms, 3.0 deprecation of legacy math. | Steering sign-off; rollback drills complete. |
| **E.4 Archive & Backlog** | Freeze roadmap, seed 3.1 backlog (auto-rank research, procedural learning). | Roadmap tagged canonical.

---

## Cross-Cutting Requirements

- **Testing**: Property tests for BHDC binding, FD PSD, procedural round-trip, meta guardrails; integration tests for unified scorer + context fusion.
- **Documentation**: Update developer guides, math playbook, ops runbooks each sprint; publish Memory Universe dashboard guide.
- **Security**: Enforce clamps, tenant isolation in meta trainer, audit logs for θ updates, PII handling in episodic logs.
- **Tooling**: CI workflow `mask-composer` replaced with `bhdc-core`; new `fd-salience` and `meta-learning` test jobs.

---

## Execution Cadence

1. **Kickoff (Week 1)**: Stand up lane leads, confirm legacy purge scope, align acceptance tests.
2. **Bi-weekly Syncs**: Lane leads share dependencies; D lane validates metrics gating before flag flips.
3. **Pre-Launch Review (Week 12)**: All lanes must present metrics + rollback playbooks; failure blocks E.2.
4. **Post-Launch Audit (Week 16)**: Verify dashboards, metrics, and retro; archive doc as canonical reference.

---

*Prepared by GitHub Copilot – canonical roadmap for the BHDC-era SomaBrain. Update only when scope changes are ratified.*