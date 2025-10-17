# Roadmap Canonical — SomaBrain v3.0

Last updated: 2025-10-17

This canonical roadmap fuses the Brain 3.0 mathematical mandate with the final architecture and implementation plan for SomaBrain v3.0. It remains the single source of truth. No mocks, no bypasses, and no undocumented workstreams.

---

## 0) Executive Summary

SomaBrain v3.0 evolves the platform into a governed, multi-tenant cognitive memory system with stable recall at scale, hot-reloadable configuration, and guardrails for every operational surface. The pillars:

- **Interference governance**: exponential decay, orthogonal key rotation, cleanup networks.
- **Tiered memory**: working memory (WM) plus long-term memory (LTM) with hierarchical recall.
- **Dynamic configuration**: live-tunable parameters through a supervisor-driven control-plane.
- **Edge governance**: Kong gateways provide auth, quotas, telemetry, and schema enforcement.
- **Blue/green upgrades**: versioned stores allow safe dimension/sparsity transitions.
- **Proof-first validation**: CI benches, property tests, and SLO dashboards quantify improvements.

---

## 1) Goals & Non-Goals

**Goals**
- Preserve top-1 recall and cosine margin as memory cardinality grows.
- Ensure tenant isolation with low-latency operations and RBAC-gated config changes.
- Expose all tuning knobs via policy-validated configuration APIs.
- Establish operational rigor: metrics, SLOs, A/B validation, and safe rollout pathways.

**Non-Goals**
- Replace HRR/BHDC algebra (we govern it; we do not change its core math).
- Embed business logic in Kong—I/O governance only.

Principles: mathematical truth, zero approximation, strict-real by default, durability-first, observable, idempotent, property-tested.

---

## 2) Architecture Overview

```
Users/Agents → Orchestrator → Kong (Gateway #1: Memory Edge)
                                                         ↳ Memory Service (WM/LTM)
                                                         ↳ Metrics (/metrics)
                                       Kong (Gateway #2: Config Edge)
                                                         ↳ Config Service (API & store)
                                                         ↳ Supervisor (control loops)
                                                         ↳ Blue/Green Cutover Controller
Observability: Prometheus + Grafana (app + gateway metrics)
Storage/Index: Vector stores, ANN indices (FAISS/HNSW or equivalent)
```

Planes:
- **Data-plane**: Memory service executes HDM operations, manages WM/LTM traces, cleanup, ANN persistence.
- **Control-plane**: Supervisor ingests metrics, computes targets, persists deltas through Config Service.
- **Edge-plane**: Kong applies auth/quotas, enforces schemas, audits, and emits ingress telemetry.

---

## 3) Math & HDM Governance

**Baseline algebra**: Circular convolution for binding, correlation/inversion for unbinding, renormalised superposition.

**Governance extensions**
1. **Exponential decay**: `(M_{t+1} = norm((1-η)M_t + η·bind(k_t', v_t)))` bounds interference.
2. **Orthogonal key rotation**: `k' = R @ k` with seeded orthonormal matrices to stabilise independence.
3. **Cleanup networks**: ANN-backed nearest-neighbour snap post-unbinding boosts top-1 accuracy.

**Tiered memory**
- WM (D=512–1024, high η, rotation on, ANN cleanup, short half-life).
- LTM (D=2048–8192, low η, rotation fixed/off, ANN/exact cleanup, policy-gated writes, optional sparsity).

Sizing guide: effective interferers `N_eff ≈ ŵ · T½ · ln 2`; dimension `D ≈ α · N_eff` with `α∈[6,10]`; value sparsity `s∈[0,1]` for archival paths.

---

## 4) APIs (External)

**Memory API** (via Kong Memory Edge)
- `POST /memory/remember` `{tenant, namespace, key, value, meta}`
- `POST /memory/recall` `{tenant, namespace, key, topk?, layer?}` → recall results with provenance
- `GET /metrics`

**Config API** (via Kong Config Edge)
- `GET /memory/config?tenant=&ns=`
- `PATCH /memory/config?tenant=&ns=` for `{dim, eta, sparsity, rotation, cleanup, scorer, gate, retention}`
- `POST /memory/cutover` `{fromNs, toNs}` with guard checks

Auth: JWT/OIDC at gateway, revalidated in app. Quotas via Kong rate-limit plugins.

---

## 5) Config Model (Effective State)

```json
{
   "tenant": "acme",
   "namespace": "wm",
   "dim": 1024,
   "eta": 0.06,
   "key_rotation": { "enabled": true, "seed": 31415 },
   "cleanup": { "mode": "ann", "topk": 64, "hnsw": { "M": 32, "efSearch": 128 }},
   "sparsity": 1.0,
   "scorer": { "w_cos": 0.6, "w_spec": 0.3, "w_rec": 0.1, "half_life_sec": 2700 },
   "gate": { "tau": 0.65, "negatives": 199, "promotion": "margin>=0.1" },
   "retention": { "ttl_seconds": 86400, "max_items": 50000 },
   "targets": { "top1": 0.90, "margin": 0.12 }
}
```

Config Service merges global → tenant → namespace layers. Supervisor writes deltas, Memory Service hot-reloads with dampers on drift.

---

## 6) Data-Plane Components

- **SuperposedTrace**: maintains `M` with decay, rotation, renorm.
- **ANN Index**: per namespace vectors for cleanup/lookup.
- **Hierarchical Recall**: WM → fallback to LTM based on confidence threshold `τ`; optional promotion.
- **Scorer**: weighted blend of cosine, spectral, recency; parameters tunable via config.
- **Numerical hygiene**: renorm after bind/unbind, `ε` safeguards, FFT plan reuse.

---

## 7) Edge Plane (Kong)

- **Gateway #1 (Memory Edge)**: routes `/memory/*`; plugins for JWT, rate limits, Prometheus, request-transform (tenant injection), structured logs.
- **Gateway #2 (Config Edge)**: routes `/memory/config` and `/memory/cutover`; plugins for RBAC, schema validation, audit, Prometheus.
- Optional Kong Mesh for service-to-service mTLS, retries, and timeouts.

---

## 8) Control Plane (Supervisor & Config Service)

- Supervisor ingests metrics (`recall_top1`, `margin_mean`, `capacity_load/dim`, `latency`, `ann_recall`).
- Policies adjust `η`, ANN parameters, thresholds, sparsity within bounded step sizes.
- Config Service persists history, publishes deltas, and provides audit trails.
- Local dampers prevent oscillation; bounded parameter deltas per minute.

---

## 9) Observability & SLOs

Metrics:
- `somabrain_memory_items{tenant,ns}`
- `somabrain_eta{ns}`, `somabrain_sparsity{ns}`
- `recall_top1_accuracy{tenant,ns}`, `cosine_margin_mean{tenant,ns}`, `snr_estimate{tenant,ns}`
- `recall_latency_seconds{ns}` (histograms), `ann_latency_seconds{ns}`
- `gateway_requests_total{route,tenant}`
- `controller_changes_total{param}`, `config_version{tenant,ns}`

Dashboards: per-namespace accuracy/margin/SNR, capacity load, ANN health, gateway errors; fleet-level latency and cost heatmaps; blue/green status.

SLO anchors: top-1 ≥ target, recall p95 latency ≤ budget, error rate ≤ ceiling.

---

## 10) Hot-Reload & Blue/Green Upgrades

Never mutate active stores. Use versioned namespaces `ns@vN`:
1. Create shadow store (v2) + ANN.
2. Dual-write new items to v1 and v2.
3. Shadow-read v2 for telemetry validation.
4. Cutover via `/memory/cutover` when SLOs green.
5. Retire v1 post rollback window.

In-place dimension changes discouraged; prefer versioned cutovers.

---

## 11) Security & Multi-Tenancy

- JWT/OIDC enforced at gateway, claims revalidated in service.
- Per-tenant quotas and namespace RBAC; optional OPA policies to bound parameter deltas (`Δη`, `Δs`, `Δτ`).
- Audit every config mutation with diff + actor.
- Resource guards for compute and storage per tenant.

---

## 12) Testing & Benchmarks

- **Unit**: HRR invariants, rotation orthogonality, cleanup correctness.
- **Property**: exponential decay behaviour, margin improvements via cleanup.
- **Integration**: hierarchical recall paths, config hot-reload, Kong ingress flows.
- **Bench** (`scripts/prove_enhancement.py`): baseline vs enhanced accuracy/margin, ANN sweeps, WM vs LTM throughput; fail build if uplift not strictly positive.

---

## 13) CI/CD & Rollout

- Pipeline: lint → type check → unit/property tests → integration (docker-compose) → bench job.
- Canary: enable governance features in WM staging before LTM.
- Feature flags for rotation, cleanup, decay per namespace; enforced by Config Service.
- GitOps for Kong manifests stored under `infra/gateway/`.

---

## 14) Runbooks

- **Parameter drift**: if `top1<target` and `capacity_load/dim>β`, bump `η` (+0.01, max 0.2), raise ANN `ef` (+16, max 512), lower `τ` (-0.02); re-evaluate after 10 minutes.
- **Cutover**: create `ns@v2`, dual-write, monitor dashboards ≥1h, execute `/memory/cutover`, keep rollback path warm.
- **ANN rebuild**: stagger shards, monitor latency, apply recall QPS backpressure during rebuilds.

---

## 15) Risk Register

- **Latency creep**: monitor p95/p99, auto-tune `ef/topK`, enforce shedding.
- **Controller thrash**: dampers, hysteresis, bounded step sizes, rollbacks.
- **Tenant overuse**: quotas + rate limits; backoff on exceedance.
- **Cutover failure**: keep v1 hot, single action rollback, health gates before switching.
- **Numerical instability**: renorm, epsilon guards, FFT plan reuse.

---

## 16) Milestones

**Milestone A — Governance Core (2–3 weeks)**
- Implement decay/rotation/cleanup, ANN integration, scorer parameters, unit + property tests.
- Sprint A1 (in progress): Added `somabrain/memory/superposed_trace.py` with exponential decay, orthogonal rotation, and cleanup anchors plus unit tests (`tests/test_superposed_trace.py`).

**Milestone B — WM/LTM Split & Hierarchical Recall (1–2 weeks)**
- Namespace separation, promotion policies, integration tests.
- Sprint B1 (in progress): Added `TieredMemory` with working/long-term coordination (`somabrain/memory/hierarchical.py`) and regression tests in `tests/test_hierarchical_memory.py`.

**Milestone C — Config & Supervisor (2 weeks)**
- **Sprint C1 (complete)**: `ConfigService` merge/audit/pub-sub flow plus `ParameterSupervisor` metrics-driven adjustments with unit tests (`tests/test_config_service.py`, `tests/test_parameter_supervisor.py`).

**Milestone D — Kong Edge (1 week)**
- **Sprint D1 (complete)**: Declarative manifests for memory/config gateways in `infra/gateway/` with JWT, rate limits, Prometheus, and log sinks.

**Milestone E — Observability & Bench (1 week)**
- **Sprint E1 (complete)**: Governance gauges/histograms in `somabrain/metrics.py` and CI-ready `scripts/prove_enhancement.py` with regression tests.

**Milestone F — Blue/Green Mechanics (1 week)**
- **Sprint F1 (complete)**: `CutoverController` blue/green orchestrator and readiness tests (`tests/test_cutover_controller.py`).

**Milestone G — Hardening & Launch (1–2 weeks)**
- **Sprint G1 (complete)**: supervisor change telemetry, cutover guardrails, and roadmap alignment updates ahead of launch.

Parallel waves continue to frame staffing focus: Mathematical Core, Memory & Durability, Observability & Verification, Resilience & Consistency, Integration & Validation. Sprints remain weekly, with the above milestones mapped across ~10 weeks.

---

## 17) Learning Brain Stability Addendum (Oct 2025)

Objective: maintain ≥70% top-1 at 5k memories while enforcing strict-real policies and invariants.

**Sprint L1 — Foundations (1.5 weeks)**
- Repair unitary-role checks in `somabrain/quantum.py`, expand BHDC property tests, update math docs.

**Sprint L2 — Unified Recall Stability (2 weeks)**
- Redesign recency damping in `memory_client._rescore_and_rank_hits`, restore density-aware cleanup, tune context management, extend benchmarks with accuracy vs capacity curves.

**Sprint L3 — Validation (2.5 weeks)**
- Integrate long-run soak tests, enforce strict-real across memory client paths, update Prometheus/Grafana assets, document configuration knobs, validate full suite.

Guardrails: deterministic operations with instrumentation, zero mock fallbacks, telemetry-first detection.

---

## 18) Strict-Real Mode & Fallback Policy

- `ALLOW_JOURNAL_FALLBACK=0` in production—no silent journaling.
- Errors bubble when outbox enqueue/publish fails; metrics flag incidents.
- Optional fallback requires explicit opt-in and surfaces via `somabrain_audit_journal_fallback_total`.

---

## 19) Mathematical Verification Metrics

- `quantum_hrr_spectral_property`, `quantum_binding_accuracy`, `quantum_role_orthogonality`, `density_matrix_trace`.
- `math_invariant_verified_total`, `property_test_passed_total`, `mathematical_proof_verified`.
- `operation_mathematical_correctness`, `implementation_truth_verified`, `mathematical_guarantee_maintained`.
- Infra exporters: Kafka, Postgres, Redis health.

Acceptance criteria: HRR spectral stability, invertible binding/unbinding, PSD density matrices, property-test coverage, live verification metrics, end-to-end tests proving correctness.

---

## 20) Migration Plan (Journal → Outbox)

1. Implement `scripts/journal_to_outbox.py` for deduplicated migration.
2. Run under operator supervision, verify outbox counts, replay until clear.
3. Disable journal fallback once backlog zero and metrics stable.

---

## 21) Immediate Next Steps

1. Confirm initiation of Milestone A work (decay/rotation/cleanup integration, ANN, scorer).
2. Prepare Alembic migration + `somabrain/db/outbox.py` skeleton to align with strict-real logging (pending confirmation).
3. Stand up Kong declarative manifests in `infra/gateway/` prototype branch for review.

When priorities or timelines shift, update this document—no side documents. This remains the canonical plan.
