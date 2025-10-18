# Roadmap Canonical — SomaBrain (Code-Aligned Edition)

Last updated: 2025-10-17  
Source of truth: this document + repository state (tags: `bhce-core`, HEAD)

---

## 0) Executive Summary

SomaBrain today runs on a **BHDC hyperdimensional core**, a **multi-tenant working-memory tier**, and an **HTTP long-term memory client**. The runtime already benefits from sparse permutation binding, a unified scoring stack, backend-enforced guardrails, and comprehensive metrics hooks. However, several roadmap promises (tiered SuperposedTrace recall, ANN cleanup, hot-reload supervisors, Kong enforcement, blue/green cutovers) remain scoped but **not wired into production paths**.

V3 success hinges on three fronts:

1. **Productionise governance math:** move from legacy WM+HTTP recall to the SuperposedTrace/TieredMemory stack, backed by ANN cleanup and real interference metrics.
2. **Close the control loop:** finish hot-reload plumbing (ConfigService events → memory plane), run the ParameterSupervisor against live telemetry, and expose `/memory/cutover`.
3. **Operational hardening:** eliminate journal fallbacks in backend-enforced mode, deliver observability on η/τ/SNR, and complete Kong edge policies.

This document supersedes prior narrative-only roadmaps. Every claim is backed by code in `somabrain/`. Deviations are explicit gaps with owners and milestones.

---

## 1) Guiding Principles (Code-Verified)

- **Mathematical truth first:** BHDC permutation binding (`somabrain/quantum.py`) is the only production binding path. Numerical invariants are recorded via `MathematicalMetrics`.
- **Backend-enforced default:** When `require_external_backends` is asserted (settings or env), stub fallbacks raise immediately. Journaling still exists in the memory service and is a critical gap (see §7).
- **Configurability with guardrails:** ConfigService merges layers in-process; no external store yet. Supervisor is implemented but idle.
- **No mock shortcuts:** Tests rely on real modules (`tests/test_superposed_trace.py`, `tests/test_hierarchical_memory.py`, `tests/unit/test_memory_client_recency.py`).

---

## 2) Current System Snapshot

| Layer | Reality today | Notes |
| --- | --- | --- |
| **Ingress** | FastAPI (`somabrain/api/memory_api.py`, `…/config_api.py`) behind planned Kong manifests | Kong configs exist but miss schema/audit plugins; no cutover route. |
| **Working Memory** | `MultiTenantWM` + `UnifiedScorer` (`somabrain/mt_wm.py`, `somabrain/scoring.py`) | Capacity, recency, density-aware cleanup implemented. No SuperposedTrace wiring. |
| **Long-Term Memory** | `MemoryClient` proxy to HTTP service (`somabrain/memory_client.py`) | Still uses journal fallback on failures; ANN search delegated to backend. |
| **Governance Math** | `SuperposedTrace`, `TieredMemory` exist with decay/rotation/cleanup (`somabrain/memory/superposed_trace.py`, `hierarchical.py`) | Not instantiated in FastAPI pipeline; cleanup is linear scan over anchors. |
| **Control Plane** | `ConfigService` + `ParameterSupervisor` + `CutoverController` implemented (`somabrain/services/*.py`) | No runtime scheduler/subscribers. Config API limited to GET/PATCH. |
| **Metrics** | Extensive collectors in `somabrain/metrics.py`; `record_memory_snapshot` called with item counts only | η/sparsity/margin/config_version gauges unused; ANN latency histogram unpopulated. |
| **Runbooks & Automation** | Scripts and docs reference blue/green, journal migration | `scripts/journal_to_outbox.py` missing; no automation for cutover controller. |

---

## 3) Math & Scoring Reality

### Implemented
- **BHDC binding & permutation unbinding** (`QuantumLayer.bind/unbind`).
- **UnifiedScorer** combining cosine, FD projection, and recency, with clamp telemetry (`somabrain/scoring.py`).
- **Working-memory density factor** reduces scores based on cleanup overlap (`somabrain/wm.py`).
- **Metrics instrumentation** for spectral invariants (`somabrain/quantum.py`), scorer components, cleanup calls (`somabrain/metrics.py`).

### Missing / Pending
- Production rollout of `SuperposedTrace` and `TieredMemory` (currently unit-tested only).
- ANN cleanup networks (HNSW/FAISS) for WM/LTM; `_cleanup` is a simple dict iteration.
- Live SNR tracking; `snr_estimate` metric defined but unused.

---

## 4) API Surfaces (Effective Behaviour)

### Memory API (`somabrain/api/memory_api.py`)
- `/memory/remember`, `/memory/remember/batch` write to LTM via `MemoryService` (`aremember`, `aremember_bulk`) and opportunistically admit items into WM using the embedder.
- `/memory/recall` performs WM cosine recall and LTM HTTP recall separately, merges results, and tracks WM/LTM latencies.
- `/memory/recall/stream`, `/memory/context/{session}` deliver session caching.
- `/metrics` exposes Prometheus metrics gathered via `record_memory_snapshot`.

### Config API (`somabrain/api/config_api.py`)
- `/config/memory` GET returns merged config snapshot.
- `/config/memory` PATCH writes to namespace layer with in-memory audit.
- **Not implemented:** `/memory/cutover`, supervisor triggers, Kong ACL enforcement.

---

## 5) Observability & SLO Tracking

Implemented collectors:
- `somabrain_memory_items`, `somabrain_eta`, `somabrain_sparsity`, `somabrain_cosine_margin_mean`, `somabrain_config_version`.
- Stage latency histograms for WM/LTM recall, ANN latency buckets, supervisor change counters.

Gaps:
- `record_memory_snapshot` only sets WM items.
- No ANN latency samples (no ANN path).
- No automated updates for η/sparsity/margin/config_version after config patches.
- `observe_ann_latency` unused; `mark_controller_change` only triggered in tests.

---

## 6) Security & Multi-Tenancy Reality

- JWT/OIDC enforcement is expected via Kong; manifests include JWT + rate-limit plugins but lack tenant header injection, schema validation, or audit logging.
- Within FastAPI, tenant IDs are trusted from request body; no RBAC hooks yet.
- Backend-enforced switch disables local stub fallbacks but journal fallback still persists data locally when upstream fails.

---

## 7) Known Gaps & Remediation Tracks

1. **Tiered Governance Integration**
   - Instantiate `TieredMemory` per tenant/namespace.
   - Route `/remember` and `/recall` through SuperposedTrace.
   - Surface confidence, margin, and rotation seeds in responses/metrics.

2. **Cleanup & ANN Indexing**
   - Replace dict cleanup with ANN (candidate: FAISS or HNSWLib).
   - Maintain indices per namespace with hot-updates from SuperposedTrace anchors.
   - Export ANN latency and accuracy metrics.

3. **Control Plane Activation**
   - Extend Config API with `/memory/cutover`.
   - Add async subscriber in memory service to apply ConfigService deltas (with dampers).
   - Schedule `ParameterSupervisor.evaluate` against Prometheus snapshots.

4. **Strict-Real & Durability**
   - Implement `scripts/journal_to_outbox.py` + `somabrain/db/outbox.py`.
   - Gate journal fallback behind explicit allow-list; fail fast otherwise.
   - Emit `somabrain_audit_journal_fallback_total` when fallback used.

5. **Kong Edge Hardening**
   - Inject tenant IDs via request-transformer.
   - Add schema validation and audit logging.
   - Ensure `/memory/cutover` route is exposed with RBAC.

6. **Telemetry Completion**
   - Populate η/sparsity/margin/config_version metrics on config changes.
   - Record ANN and overall SNR metrics from TieredMemory.
   - Build dashboards for margin vs capacity, ANN health, blue/green readiness.

---

## 8) Milestones (Delivered & Upcoming)

### Delivered (code verified)
- **BHDC Core (A1)** — `somabrain/quantum.py`, tests for spectral/orthogonality.
- **Unified Scorer (A2)** — `somabrain/scoring.py`, WM density adjustments.
- **Config Foundations (C1)** — `ConfigService`, `ParameterSupervisor`, tests.
- **Metrics Base (E1)** — Governance gauges and `scripts/prove_enhancement.py`.

### Upcoming (execution required)
| Milestone | Goal | Owner modules | Exit criteria |
| --- | --- | --- | --- |
| **M1: Tiered Memory Activation** | Replace WM/LTM recall with `TieredMemory` | `somabrain/api/memory_api.py`, `somabrain/memory/hierarchical.py` | `/recall` emits layer+margin; WM/LTM share SuperposedTrace; tests updated. |
| **M2: ANN Cleanup** | Introduce HNSW/FAISS indices | new `somabrain/ann/`, `superposed_trace.py` | Cleanup latency <40 ms; top-1 uplift vs baseline recorded in CI bench. |
| **M3: Control Loop Live** | Hook supervisor + cutover endpoints | `somabrain/services/*`, config API, runtime scheduler | Supervisor adjusts η/τ/ef; `/memory/cutover` transitions namespaces; metrics show controller changes. |
| **M4: Strict-Real Durability** | Remove silent journaling | `somabrain/services/memory_service.py`, new migration script | Production mode raises on failure; migration tool clears journals; metrics for fallback. |
| **M5: Edge Enforcement** | Harden Kong manifests | `infra/gateway/*.yaml` | Tenant header injection, schema validation, audit logs deployed. |
| **M6: Observability Closure** | Feed full telemetry set | `somabrain/metrics.py`, updated callers | Dashboards populated; CI asserts metric emission. |

---

## 9) Execution Waves & Sprints (Simple, Precise)

**Wave 1 — Governance Activation (Weeks 1–2)**
- ✅ *Sprint 1A:* TieredMemory now fronts recall with governed margin/confidence (`somabrain/api/memory_api.py`) and snapshot tests cover tiered hits.
- ✅ *Sprint 1B:* Cleanup index is pluggable (`somabrain/services/ann.py`, env-driven HNSW fallback) and wired through `TieredMemoryRegistry`.
- ✅ *Sprint 1C:* `/memory/recall` feeds η/sparsity/margin into `record_memory_snapshot`; governance payloads carry `governed_margin` for benches.

**Wave 2 — Control Loop & Durability (Weeks 3–4)**
- ✅ *Sprint 2A:* ConfigService now dispatches events via `config_runtime`, TieredMemory hot-reloads (`somabrain/api/memory_api.py`, `somabrain/services/tiered_memory_registry.py`), and `/config/cutover/*` endpoints drive the controller.
- ✅ *Sprint 2B:* ParameterSupervisor runs from the runtime dispatcher, consumes recall telemetry, and patches config while emitting controller-change metrics.
- ✅ *Sprint 2C:* Added `scripts/journal_to_outbox.py`, disabled journal fallback by default (`allow_journal_fallback`), and wired backend-enforced documentation.

**Wave 3 — Edge & Learning Integrations (Weeks 5–6)**
- ✅ *Sprint 3A:* Hardened Kong manifests (tenant headers, schema validation, audit streaming) in `infra/gateway/`.
- ✅ *Sprint 3B:* Pluggable ANN backend now tunable with rebuild job + admin endpoint (`somabrain/services/ann.py`, `tiered_memory_registry.py`, `/memory/admin/rebuild-ann`).
- ✅ *Sprint 3C:* Drafted learning-loop design (`docs/development-manual/learning-loop.md`), shipped dataset builder (`somabrain/learning/dataset.py`) and export CLI.

Each sprint ships independently, keeps interfaces minimal, and updates this roadmap with results and metrics.

---

## 9) Testing & Bench Coverage

- **Unit tests:** BHDC invariants (`tests/test_quantum_layer.py`), SuperposedTrace, TieredMemory, ConfigService, ParameterSupervisor, unified scorer recency behaviour.
- **Integration gaps:** no end-to-end tests for TieredMemory recall or config hot-reload.
- **Benchmarks:** `scripts/prove_enhancement.py` compares baseline vs enhanced metrics but requires updated datasets reflecting ANN/TieredMemory once implemented.

Planned additions:
- Property tests for interference scaling (SuperposedTrace).
- Integration suite for supervisor-driven config adjustments.
- Bench job validating ANN uplift and latency regressions.

---

## 10) Immediate Action Items

1. **Design doc & spike:** Outline TieredMemory adoption plan (tenants, persistence strategy) and create integration tests.
2. **Stand up ANN prototype:** Choose FAISS/HNSW binding, design anchor ingestion + async rebuild path. *(In progress via pluggable backend; finalize benchmark + config knobs.)*
3. **Implement journal migration script** and flip backend-enforced default once validated. ✅ (Script shipped; backend-enforced mode now rejects journaling.)
5. **Update Kong manifests** with tenant injection, schema validation, audit logging.
6. **Wire telemetry emitters** for η/sparsity/margin/config_version and confirm dashboards.

---

## 11) Ownership & Tracking

- **Math & Governance:** Math core team (owners: `somabrain/quantum.py`, `somabrain/memory/superposed_trace.py`).
- **Memory Service & API:** Platform integrations (owners: `somabrain/api/memory_api.py`, `somabrain/services/memory_service.py`).
- **Control Plane:** Control systems team (`somabrain/services/config_service.py`, `parameter_supervisor.py`, `cutover_controller.py`).
- **Edge & Observability:** Infra/SRE (Kong manifests, Prometheus dashboards, journaling remediation).

Track milestones via GitHub project **“Brain v3 – Implementation”**, using these labels: `math-governance`, `tiered-memory`, `ann-cleanup`, `control-plane`, `backend-enforced`, `edge`.

---

## 12) Canonical References

- **Implementation:** See referenced modules in this doc; repository tags `bhce-core`, `v2.9`.
- **Docs:** ADR-003 (BHDC adoption), Technical Architecture manual (`docs/technical-manual/architecture.md`) for conceptual background.
- **Tests:** `tests/` directory for coverage, `scripts/prove_enhancement.py` for CI bench.

This roadmap is authoritative. Update it with every delivered milestone or scope change; link commits and PRs directly. No external spreadsheets or shadow docs.
