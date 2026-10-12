# SOMA-BR-MASTER-REMEDIATION-001 — SomaBrain × SomaFractalMemory Master Remediation Plan

## Document Control

| Field | Value |
|---|---|
| Document Title | Master Remediation Plan — Single-Lane Architecture, Fail-Closed Perfection, Admin UI |
| Document Identifier | SOMA-BR-MASTER-REMEDIATION-001 |
| Version | 1.0.1 |
| Date | 2026-10-09 |
| Status | Draft |
| Author | SomaTech Engineering |
| Approver | Product Owner |
| Classification | Internal |
| ISO Reference | ISO 9001:2015 — Quality Management Systems — Requirements |
| Next Review | 2027-01-09 |
| Related | SOMA-STD-TRIAD-001 · SOMA-BR-DEBT-001 · SOMA-BR-ARCH-TRUTH-001 · SOMA-BR-MATH-TRUTH-001 · SOMA-UI-IA-001 · SOMA-UI-SPEC-001 · UI-S-56 |
| Source of truth | Code in `somabrain/` and `somafractalmemory/`; this plan records intent and status only |
| Scope | Single-lane remediation waves A–D across the SomaBrain / SomaFractalMemory pair |
| Audience | SomaTech engineering agents and operators |

## Revision History

| Version | Date | Author | Description |
|---|---|---|---|
| 1.0.0 | 2026-10-09 | SomaTech Engineering | Initial master remediation plan (Rust default, Admin UI, waves). |
| 1.0.1 | 2026-10-09 | SomaTech Engineering | Document Control table added (SOMA-BR-DOCS-001). Wave A status truth: DEBT-008/A2/A5 fail-closed DONE; stale `return []` live claims removed. |

---

## 1. Purpose

Remediate `somabrain` and `somafractalmemory` to:

1. **Single-lane authorities** — one adaptation engine, one transport, one math home, one neuromod store, one settings law.
2. **Rust as the default hot-path engine** (Python orchestrates, Rust computes).
3. **Zero fallbacks** — every path either works or fails closed with a typed error. No silent empty, no soft default, no dead code.
4. **SomaBrain Administration UI** — full system/settings management surface on the SomaTech / YACHAQ design language.
5. **ISO documentation** for every deliverable.

Out of partition: `somaAgent01/webui/` (do not edit). Admin UI lives in `somabrain` (or `somaAgent01` only if owner re-partitions).

---

## 2. Opinion — Rust as default hot path (ADOPTED)

**Decision: Rust owns compute. Python owns orchestration and I/O.**

| Layer | Owner | Rationale |
|---|---|---|
| HTTP API, auth, OPA, Temporal/outbox orchestration, Django models | **Python** | Ecosystem, velocity, Ninja/FastAPI surface |
| Adaptation gains (APM-1), ranking / scoring math, HRR / QuantumLayer, recency, BHDC, embedding math, percentile moments | **Rust (`rust_core`)** | Deterministic, fast, no GIL, measurable |
| FFI boundary | Single `rust_bridge` / PyO3 module | One authority, thin Python callers |

**Why this is correct (not cargo-cult):**
- The current DEBT-008 failure mode (Python vs Rust adaptation gains differ in sign and magnitude) is exactly what dual-implementation always produces. We do **not** keep both and "prefer Rust at runtime" — we **delete the Python twin** and call Rust.
- Speed hits matter on the T-6 accept path (today 160–250 ms residual) and ranking of large hit sets. Those are Rust-shaped problems.
- Fail-closed is easier to prove in one implementation than in two that must stay in sync.

**What we will NOT do:** rewrite Django/Ninja/Temporal in Rust. Orchestration stays Python; math becomes Rust-only.

**Rule (new, binding):** *No algorithm may exist in both languages. If it is in `rust_core`, Python must call it. If it is in Python, `rust_core` must not reimplement it.*

---

## 3. Appreciation — is this the best memory system in the world?

**Honest assessment: it is architecturally world-class and product-incomplete.**

What is genuinely excellent:
- **T-6 durable-before-hop** with outbox + `FOR UPDATE SKIP LOCKED` + lease — most "memory systems" lose writes under crash; this one does not.
- **`mem:{coord}` idempotency** with content-equal replay vs 409 on payload mismatch — rare and correct.
- **Fail-closed recall** (`MemoryRecallUnavailable`, never `[]` on outage) on the live hot path — this is the difference between a demo and infrastructure.
- **Dual-store truth discipline** (Postgres record + Milvus ANN, 768-dim honesty) — right model.
- **One neuromod store, one math contracts home, settings-law sweep** — self-discipline most codebases never reach.
- **Memory-event → APM-1 learning loop** with per-tenant engines — a real cognitive memory, not a vector DB wrapper.

What kept it from being *the* best (status 2026-10-09, Wave A landed):
1. Dual Rust/Python adaptation authority (DEBT-008) — **CLOSED**. Rust `somabrain_rs` is the sole adaptation-math authority.
2. Parallel transports to one seam — single Brain→SFM header builder `memory/sfm_auth.build_sfm_request_headers` (R5); `MemoryClient` is HTTP-only.
3. Outage `return []` swallows (`hybrid.py`, `utils.fetch_by_coord`, `milvus_ann`) — **DELETED / fail-closed**. `hybrid.py` removed; `fetch_by_coord`, `milvus_ann.search`, `payloads_for_coords` raise; `remember_bulk` partial failure raises with failed indexes.
4. Client-path idempotency (H3) — **DONE**: outbox `IntegrityError` is an idempotent replay; `aremember_background` raises (H4); `mark_sent` warns on failure (M5).
5. No Administration UI — still the remaining gap (Wave C).

**Conclusion:** With Wave A–D below done, this *can* be the best memory system in the world — the bones are better than almost anything public. The work is deletion, single-lane enforcement, and an operator-grade admin surface — not more features.

---

## 4. Design standard (Admin UI + all surfaces)

**Authoritative brand (live sites, 2026-10-07):**

| Token | Value | Use |
|---|---|---|
| Brand orange | `#FF4D00` | Primary CTA, active nav, focus ring, brand chrome |
| Soft orange | `#FF7A3D` | Hover, secondary brand |
| Deep orange | `#E64500` | Pressed, deep accent |
| Black void | `#050505` | Page background (dark) |
| Surface dark | `#0A0A0A` / `#121212` | Cards, panels |
| Error | `#EF4444` | Errors only — never brand |
| Success | `#10B981` | Health OK |
| Warning | `#F59E0B` | Degraded |
| Info | `#FF7A3D` | Neutral info |
| Font UI | **Inter** (300–700) | All UI |
| Font mono | **JetBrains Mono** | Metrics, codes, IDs, logs |

**Forbidden:** violet/purple brand chrome (`#E64500`, `#7C3AED`) — owner rejected. Purple may appear only as a data-viz series, never as brand.

**Dark-first** with light theme via `data-theme="light"` using `somastack-ui.css` tokens (refactor accent to orange).

**A11y law (WCAG 2.2 AA):** `:focus-visible` 2px `#FF4D00` (≥3:1 on dark), `role="status"`/`role="alert"` on all async, labels `for`/`id`, chart `role="img"` + text alternative, tab semantics, no color-only status.

**Chrome law:** follow `SOMA-UI-IA-001` — admin is **not** chat chrome. Admin lives on its own routes. Memory home stays `/memory`. Secrets never in forms (Vault pointer only).

**Existing mock to extend:** `somaAgent01/docs/design/mockups/UI-S-56-settings-somabrain.md` (connection settings). Admin product extends this into a full **SomaBrain Administration** shell.

---

## 5. Admin product — SomaBrain Administration

### 5.1 Information architecture (own routes, not chat)

```
/admin                          → Overview (health, tenants, capacity, alerts)
/admin/settings                 → System settings (BrainSetting 75-key registry, grouped)
/admin/settings/cognitive       → Cognitive / neuromod / anneal / tau
/admin/settings/memory          → WM/LTM, promotion, prune/decay, outbox
/admin/settings/learning        → APM-1, α/β/γ/τ/θ, annealing
/admin/settings/security        → OPA policies (read), auth posture, Vault pointers
/admin/tenants                  → Tenant list, isolation status, quotas
/admin/health                   → Dual-store health, circuits, accept latency, outbox depth
/admin/metrics                  → p95/p99, throughput, learning rates (text + charts)
/admin/debts                    → DEBT register (live), DELETE-or-IMPLEMENT state
/admin/audit                    → Audit log, A2A ledger view (read)
```

### 5.2 Screen families (ISO UIUX style)

| Screen | ID | Purpose |
|---|---|---|
| Admin chrome | UI-SB-00 | Sidebar + top bar + status dots (brand orange) |
| Overview | UI-SB-01 | Health rollup, tenant count, outbox depth, accept p95, alerts |
| System settings | UI-SB-02 | BrainSetting CRUD, grouped, search, diff-before-save |
| Memory settings | UI-SB-03 | WM/LTM knobs, promotion, prune, fail-closed switches |
| Learning / neuromod | UI-SB-04 | APM-1 params, neuromod store (single), anneal schedule |
| Tenants | UI-SB-05 | Tenant isolation, quotas, credential binding |
| Health & diagnostics | UI-SB-06 | Dual-store, circuits, outbox replay, milvus reconcile |
| Metrics | UI-SB-07 | Live gauges (p95/p99), accessible charts |
| Debt & compliance | UI-SB-08 | Open DEBTs, invariant scorecard, ISO register |
| Modal / confirm | UI-SB-09 | Glass modal + "Don't ask again" (no native confirm) |

### 5.3 Interaction laws
- Every writable field bound to a live API; no invented fields.
- Unavailable capabilities show a blocking reason — never a disabled ghost.
- Fail-closed in UI too: outage = explicit unavailable message, never empty success.
- Confirm destructive actions with glass modal.
- Keyboard-first, focus-visible, live regions.

---

## 6. Remediation waves

### WAVE A — Single-lane + zero dead code (correctness) — P0

| # | Action | Path | Gate |
|---|---|---|---|
| A1 | Land dirty trees (W-H1 + ADV B1/B2) when tests green | both repos | A2A claims |
| A2 | **Rust default authority (DEBT-008)**: `rust_core` sole adaptation/math hot path; Python thin FFI caller; no Python twin | somabrain `rust_core/` + `learning/adaptation/` + `math/` | **DONE** (DEBT-008 CLOSED 2026-10-09) |
| A3 | Kill predictor fallback → refuse naming setting | `bootstrap/singletons.py` | free |
| A4 | Fix `math/contracts.py:80` env default → `require_setting` | `math/contracts.py` | rows 71/72/75 |
| A5 | **Delete `memory/hybrid.py`** + regression guard "no callers" | `somabrain/memory/hybrid.py` | **DONE** (WAVE A5, RELEASED) |
| A6 | `utils.fetch_by_coord` raise or delete + re-point export | `memory/utils.py` | free |
| A7 | `milvus_ann.search` raise on outage (no `[]`) | `services/milvus_ann.py` | ACK T-5 seats |
| A8 | Client-path outbox `IntegrityError` → idempotent replay | `memory/remember.py` | INBOX W0 |
| A9 | `aremember_background` never silent-return | `memory/remember.py` | INBOX W0 |
| A10 | Remove `"all"` layer alias; fix `namespace` doc leak | `api/memory/helpers.py`, `models.py` | free-ish |
| A11 | Delete dead/stale: `tests/aaas/`, unused exports, `fde` provider name, `milvus_client` compat shim, placeholder-named vectors | both repos | verify no callers |
| A12 | `remember_bulk` no silent partial drop | `remember_bulk.py` | mine |
| A13 | `recall_service` fallback delete or typed non-silent | `services/recall_service.py` | R-14 |
| A14 | Sweep **every** `return []` / `return None` / `except: pass` — prove success-empty or convert to raise | both repos | test_ann_empty_is_success |

**Exit criteria:** no `return []` on outage; no fallback; no dead module; `mem:{coord}` on both paths; Rust is the only adaptation authority; full test suite green.

### WAVE B — One transport + one tenant law — P1

| # | Action | Path |
|---|---|---|
| B1 | Merge `memory/transport.py` + `memory/client/transport.py` into one module (one retry, one auth header, one timeout from contracts) | somabrain |
| B2 | gRPC `transport/` — keep only if somaAgent01 consumes it; else delete | somabrain |
| B3 | SFM `tenant="default"` defaults removed — require tenant (mirror brain T-5) | SFM `admin/core/services.py` |
| B4 | Split SFM `services.py` (966→&lt;400): `embeddings.py`, `vector_store.py`, `graph_service.py` | SFM |
| B5 | Vault client twin alignment + mirrored conformance test | both |
| B6 | Mirror `test_seam_error_taxonomy.py` (exceptions, dim 768, bearer, payload keys) | both |
| B7 | ADR: long-work authority (outbox exempt vs Temporal migration for anneal/reconcile) | both |
| B8 | HashEmbedder: real embedder default OR named degraded mode with health flag | SFM |

**Exit criteria:** one transport, one tenant rule, shared error taxonomy, SFM services split, ADR recorded.

### WAVE C — SomaBrain Administration UI — P1

| # | Action | Notes |
|---|---|---|
| C1 | Design tokens: `webui/design-system/somastack-ui.css` → orange brand `#FF4D00`, Inter + JetBrains Mono, dark-first | both sites' palette |
| C2 | Admin shell UI-SB-00 + Overview UI-SB-01 | |
| C3 | System settings UI-SB-02 (BrainSetting registry — search, group, diff, save) | live GET/PUT only |
| C4 | Memory / Learning / Security settings screens | |
| C5 | Tenants + Health + Metrics (accessible charts) | |
| C6 | Debts + Audit screens | |
| C7 | A11y pass: live regions, labels, focus, tabs, contrast | WCAG 2.2 AA |
| C8 | ISO UIUX docs: `SOMA-BR-UIUX-001..005` (screens, modals, catalogue, traceability, settings parity) | |
| C9 | Verify in browser before claiming done | golden path + edge cases |

**Exit criteria:** operator can configure every BrainSetting and see every system state without SSH/DB; WCAG AA; ISO UIUX suite published.

### WAVE D — Perfection polish + ISO — P2

| # | Action |
|---|---|
| D1 | Accept latency → single-digit ms (middleware trim, journal async) |
| D2 | Close DEBT-010/024/025/027/028 (DELETE-or-IMPLEMENT) |
| D3 | File or drop "percentile transport" / dry-run requirements |
| D4 | CLI HOST/PORT → settings chain |
| D5 | Endpoint thinning `memory_remember.py` (after claims release) |
| D6 | Update DEBT register, ARCH-TRUTH, MATH-TRUTH, VV matrix |
| D7 | Invariant scorecard re-run; live E2E + OPS-RUNBOOK proofs |

---

## 7. No-fallback law (binding)

Applies to both repos and the Admin UI:

1. Missing setting → **refuse naming the setting**. Never a default.
2. Outage → **typed raise** (`MemoryRecallUnavailable`, `VectorIndexUnavailable`, `CircuitBreakerOpen`, …). Never `[]`, never `None`, never empty success.
3. Partial batch failure → **raise listing failed indexes**. Never silent partial success.
4. Unknown provider → **refuse**. Never soft-fallback.
5. UI: unavailable capability → **blocking reason**. Never fake control.
6. Dead code is deleted, not quarantined. No TODO/FIXME/HACK/shim/stub in production paths.

---

## 8. Success metrics

| Metric | Target |
|---|---|
| Outage `return []` count | **0** |
| Fallback paths | **0** |
| Adaptation authorities | **1 (Rust)** |
| brain→SFM transports | **1** |
| `mem:{coord}` enforcement | API + client |
| DEBT-008 | CLOSED |
| High/critical findings from 2026-10-09 review | all closed |
| Admin settings coverage | 100% of BrainSetting registry |
| WCAG 2.2 AA (admin + dashboards) | PASS |
| Accept p95 | &lt; 10 ms (target) |
| Test suite | green, 80%+ on touched modules |
| Docs | ISO suite current, register consistent |

---

## 9. Execution order (next steps)

1. **Process:** claim paths in `docs/plans/a2a/CLAIMS.md`; INBOX for colliding rows (W0, W3, ADV B1/B2, row 71/72).
2. **A2A claim hygiene:** mark stale 2026-10-05 rows DONE/RELEASED.
3. **WAVE A** (this session if approved): A3, A5, A6 first (unclaimed); A2 Rust authority next; A8/A9 after INBOX.
4. **WAVE B** parallel where claims allow.
5. **WAVE C** design tokens + Admin shell (UI/UX expert seat) — start after A3–A6 so the UI is built on honest APIs.
6. **WAVE D** polish + ISO close-out.

---

## 10. Revision history

| Version | Date | Author | Change |
|---|---|---|---|
| 1.0.1 | 2026-10-09 | SomaTech Engineering | Wave A status truth: A2/A5 fail-closed DONE (hybrid.py deleted, DEBT-008 closed, H3/H4/M5 done). Removed stale 'return [] still live' claims. |
| 1.0.0 | 2026-10-09 | SomaTech Engineering | Initial master remediation plan; Rust-as-default decision; Admin UI IA; four waves. |
