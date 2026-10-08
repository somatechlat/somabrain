# SOMA-BR-DEBT-001 — Defect & Architecture Debt Register

## Document Control

| Field | Value |
|---|---|
| Document Title | Defect & Architecture Debt Register |
| Document Identifier | SOMA-BR-DEBT-001 |
| Version | 1.0.0 |
| Date | 2026-09-28 |
| Status | Draft |
| Author | SomaTech Engineering |
| Approver | — |
| Classification | Internal |
| ISO Reference | ISO 9001:2015 §8.7 Nonconforming outputs; ISO/IEC 25010 Maintainability |
| Next Review | 2026-12-28 |
| Related | `SOMA-BR-PLAN-MASTER-001.md`, `SOMA-BR-ARCH-001.md`, `SOMA-BR-RISK-001.md`, `SOMA-BR-VV-001.md` |
| Source of truth | **The code.** Every row cites `file:line` as observed in this working tree. |
| Audience | Wave leads (W1–W6), reviewers, auditors |

## Revision History

| Version | Date | Author | Description |
|---|---|---|---|
| 1.0.0 | 2026-09-28 | SomaTech Engineering | Initial issue. Every candidate claim was re-verified against the working tree. Unprovable claims were removed; newly discovered defects were added. |
| 1.1.0 | 2026-10-05 | SomaTech Engineering | W2 closed: DEBT-001…007 **FIXED**. One neuromod store (`runtime/neuromodulators.py`), DA→LR reads the singleton, homeostatic law, clamped API, shared ACh/5-HT laws with real consumers, Rust ODE deleted, Supervisor wired on `/act`. Tests: `tests/unit/test_neuromod_wiring.py`. |

## 1. Purpose

Master register of proven defects and architecture debt that later waves will fix.
This document is **evidence**, not opinion. A row exists only when the cited code
behaviour is observable at the cited `file:line`.

### 1.1 Governing rules

1. **CODE IS SOURCE OF TRUTH.** Docs, comments, and proof papers lose to code.
2. **No shims, no fakes, no bypasses, no stubs as fixes.** Required-fix text never
   uses those words as a strategy. Every fix is either **DELETE** or **FULL IMPLEMENT**.
3. **Every row has `file:line`.** Speculative defects are forbidden.
4. **Acceptance is executable.** Each row states a test that fails before the fix
   and passes after.

### 1.2 Severity scale

| Severity | Meaning |
|---|---|
| **P0** | Incorrect values, wrong signs, or crashes on the production path. Learning, scoring, or memory ranking is wrong today. |
| **P1** | Divergent dual implementations, dead production machinery, or numeric formulas that disagree with their own tests/docs. Silent wrong answers or unbounded drift. |
| **P2** | Unused subsystem, incomplete cognitive module, or documentation debt with no direct runtime corruption. |

### 1.3 Wave assignment

| Wave | Scope |
|---|---|
| **W1** | Contracts — single source for λ*(p), gains, τ, recency, bounds |
| **W2** | Neuromod — single store tree, clamped API, live dynamics or deletion |
| **W3** | Mathcore — Wiener λ*, Theorem 1, gains signs, binder, predictors, Rust tests |
| **W4** | Memory — recency, lexical bonus, scorer constructor, FD-off scoring |
| **W5** | Cognition — basal ganglia, prefrontal, personality |
| **W6** | Docs-sync — proof documents rewritten from code |

---

## 2. Summary Register

| ID | Sev | Subsystem | Wave | One-line defect |
|---|---|---|---|---|
| DEBT-001 | P1 | Neuromod | W2 | Dual neuromodulator trees (`admin/brain` vs `runtime`) — **FIXED (W2)** |
| DEBT-002 | P0 | Neuromod | W2 | DA→LR reads a fresh empty `PerTenantNeuromodulators()` every call — **FIXED (W2)** |
| DEBT-003 | P0 | Neuromod | W2 | API `/neuromod/adjust` writes unclamped values — **FIXED (W2)** |
| DEBT-004 | P1 | Neuromod | W2 | Adaptive feedbacks are non-negative → parameters saturate at max — **FIXED (W2)** |
| DEBT-005 | P1 | Neuromod | W2 | ACh coupling disagrees with its own comment and with Supervisor — **FIXED (W2)** |
| DEBT-006 | P2 | Neuromod | W2 | Serotonin stored/exported but never consumed for control — **FIXED (W2)** |
| DEBT-007 | P1 | Neuromod | W2 | Rust neuromod ODE (`update`) is dead outside a migration script — **FIXED (W2)** |
| DEBT-008 | P0 | Learning | W3 | Python vs Rust adaptation gains differ in sign and magnitude |
| DEBT-009 | P1 | Learning | W3 | Three τ mechanisms + four floors (0.4 / 0.1 / 0.05 / 0.01) — **FIXED (W3)** — one `TAU_FLOOR=0.1` in `math/contracts.py`; `SOMABRAIN_TAU_MIN` defaults to it; `apply_tau_annealing` uses `anneal_tau(…, TAU_FLOOR)` |
| DEBT-010 | P1 | Learning | W3 | Entropy cap rewrites τ (and all retrieval weights) in place |
| DEBT-011 | P0 | Mathcore | W3 | Wiener λ* formula vs hardcoded constant — **FIXED (W4)** |
| DEBT-012 | P1 | Mathcore | W3 | Theorem 1 `p*` formula ≥ 0.5 vs comment/docs "p ≈ 0.1" — **FIXED (W4)** |
| DEBT-013 | P0 | Mathcore | W3 | Rust test constructs `BayesianMemory` with wrong arity (does not compile) — **FIXED (W4)** |
| DEBT-014 | P0 | Mathcore | W3 | Rust λ* unit test expects 2× the implementation — **FIXED (W4)** |
| DEBT-015 | P1 | Mathcore | W3 | Python binder `unbind` is plain division, not Wiener — **FIXED (W4)** |
| DEBT-016 | P1 | Mathcore | W3 | Python binder `mix="hadamard"` / FWHT is a silent no-op — **FIXED (W4)** |
| DEBT-017 | P1 | Mathcore | W3 | Chebyshev heat bounds are unexpanded Lanczos Ritz values — **FIXED (W5b)** |
| DEBT-018 | P1 | Predictors | W3 | Rust `MahalanobisPredictor.distance` is Euclidean L2 — **FIXED (W4)** |
| DEBT-019 | P1 | Predictors | W3 | Rust `SlowPredictor.error` uses \|cos\| (opposites → error 0) — **FIXED (W4)** |
| DEBT-020 | P1 | Memory | W4 | Three recency formulas; `WM_RECENCY_TIME_SCALE` has three defaults — **FIXED (W5b)** |
| DEBT-021 | P1 | Memory | W4 | Two lexical-bonus formulas (`max` vs `+`) — **FIXED (W5b)** |
| DEBT-022 | P0 | Memory | W4 | `UnifiedScorer` ignores its constructor weight arguments — **FIXED (W5b)** |
| DEBT-023 | P1 | Memory | W4 | FD-off score ceiling is 0.75 (weights not renormalised) — **FIXED (W5b)** |
| DEBT-024 | P1 | Cognition | W5 | `BasalGangliaPolicy.decide` is the identity of its gates |
| DEBT-025 | P1 | Cognition | W5 | `PrefrontalCortex.process` is a scalar gain on numeric fields |
| DEBT-026 | P0 | Cognition | W5 | `PersonalityStore.get` references undefined name `t` — **FIXED (W5b)** |
| DEBT-027 | P0 | Docs | W6 | `LEARNING_MATHEMATICAL_PROOF.md` contradicts code (gains, τ, entropy) |
| DEBT-028 | P1 | Docs | W6 | GMD / proof-report λ* and p* claims contradict code and each other |

**Totals:** P0 = 9, P1 = 17, P2 = 1. Wave: W2 = 7 (**all FIXED**), W3 = 12, W4 = 4, W5 = 3, W6 = 2.
**Fixed:** DEBT-011…016, 018, 019 (W4); DEBT-017, 020, 021, 022, 023, 026 (W5b).

### 2.1 Candidate claims removed after verification

| Candidate claim | Disposition |
|---|---|
| "Supervisor unused" | **Removed.** `Supervisor` is constructed at `somabrain/bootstrap/core_singletons.py:177-184` and consumed at `somabrain/services/cognitive_loop_service.py:219`. It is default-disabled (`SOMABRAIN_USE_META_BRAIN=False`, `somabrain/settings/cognitive.py:233`), not dead. The adjacent real defect (dead Rust ODE) is DEBT-007. |
| "SOMABRAIN_MATHEMATICAL_PROOF_REPORT.md Wiener claims" | **Narrowed.** That file states only `delta = lr × gain × signal` and a multiplicative τ anneal (`SOMABRAIN_MATHEMATICAL_PROOF_REPORT.md:93`, `:145`). The τ floor range it publishes (`floor ∈ [0.01, 0.1]`, `:155`) conflicts with settings default `SOMABRAIN_TAU_MIN=0.4` and is folded into DEBT-009 / DEBT-027. |

---

## 3. Detailed Defect Rows

### DEBT-001 — Dual neuromodulator trees

| Field | Value |
|---|---|
| **Severity** | P1 |
| **Subsystem** | Neuromod |
| **Wave** | W2 |
| **Status** | **FIXED (W2)** |
| **Resolution (W2)** | DELETED `somabrain/admin/brain/neuromodulators.py`; `runtime/neuromodulators.py` is THE store. All imports re-pointed (engine, unified_core, admin/brain/__init__ without re-export, tests). Acceptance: `tests/unit/test_neuromod_wiring.py::TestSingleStore`. |
| **Proof** | `somabrain/admin/brain/neuromodulators.py:1-424` and `somabrain/runtime/neuromodulators.py:1-449` |
| **What code does** | Two near-identical modules each define `NeuromodState`, `Neuromodulators`, `PerTenantNeuromodulators`, `AdaptiveNeuromodulators`, and the four `_calculate_*_feedback` functions. The API writes through `runtime` (`somabrain/api/endpoints/neuromod.py:32-35`, `:71-80`). Learning reads through `admin/brain` (`somabrain/learning/adaptation/engine.py:435-437`). A write to one tree is invisible to the other. |
| **What docs claim** | Module headers of both files claim the same single neuromodulatory system (`admin/brain/neuromodulators.py:1-37` = `runtime/neuromodulators.py:1-37`). |
| **REQUIRED FIX** | **DELETE** one tree. Keep a single module; re-point every import. Remove the duplicate dataclass, store, and feedback functions entirely. |
| **Acceptance test** | `rg -l "class PerTenantNeuromodulators" somabrain/` returns exactly one file. Integration test: `POST /neuromod/adjust` then `AdaptationEngine._get_dopamine_level()` observes the written dopamine. |
| **Wave** | W2 |

### DEBT-002 — DA→LR reads a fresh empty store

| Field | Value |
|---|---|
| **Severity** | P0 |
| **Subsystem** | Neuromod / Learning |
| **Wave** | W2 |
| **Status** | **FIXED (W2)** |
| **Resolution (W2)** | `_get_dopamine_level` now reads `bootstrap.singletons.get_neuromodulators()` (the store the API writes). Acceptance: `TestDopamineToLearningRate` — d=0.8 then d=0.2 changes lr_scale. |
| **Proof** | `somabrain/learning/adaptation/engine.py:431-439` |
| **What code does** | `_get_dopamine_level` does `PerTenantNeuromodulators().get_state(self._tenant_id).dopamine`. The `()` constructs a **new** store with empty `_states` (`admin/brain/neuromodulators.py:202-206`), so `get_state` falls through to `_global.get_state()` (`:217`), which is settings-default dopamine, never the tenant's adjusted value. Dynamic LR (`engine.py:356-359`) is therefore constant. |
| **What docs claim** | `LEARNING_MATHEMATICAL_PROOF.md:27` presents `weight_{t+1} = weight_t + (learning_rate × gain × signal)` as adaptive; dynamic LR is presented as neuromodulator-driven. |
| **REQUIRED FIX** | **FULL IMPLEMENT** a process-lifetime shared per-tenant store (DI container or module-level registry with locking) and inject it into `AdaptationEngine`. Delete the per-call constructor. |
| **Acceptance test** | Unit: set tenant dopamine to 1.0 in the shared store, call `_get_dopamine_level()`, assert return is 1.0 (today it returns the settings default, e.g. 0.4). |
| **Wave** | W2 |

### DEBT-003 — API neuromod adjust is unclamped

| Field | Value |
|---|---|
| **Severity** | P0 |
| **Subsystem** | Neuromod |
| **Wave** | W2 |
| **Status** | **FIXED (W2)** |
| **Resolution (W2)** | API validates via `checked_value` against `math.contracts.NEURO_BOUNDS`; out-of-box/NaN/inf rejected with 422. Store projects with Π on set_state. Acceptance: `TestApiBounds`. |
| **Proof** | `somabrain/api/endpoints/neuromod.py:20-24`, `:76-80` |
| **What code does** | `NeuromodAdjustRequest` accepts any `float`. The handler copies `float(val)` straight into `NeuromodState(**current)` with no bounds check. Documented ranges (`admin/brain/neuromodulators.py:69-76`: DA [0.2, 0.8], 5-HT [0, 1], NE [0, 0.1], ACh [0, 0.1]) are not enforced anywhere on this path. Rust `Neuromodulators.update` clamps (`rust_core/src/neuro.rs:84-87`) but is not invoked here. |
| **What docs claim** | Docstring ranges above; `somabrain/schemas/health.py:182` even types serotonin as `ge=0.0, le=1.0`. |
| **REQUIRED FIX** | **FULL IMPLEMENT** clamping at the boundary using the same bounds as `NeuromodState` / Rust `update`. Reject or clamp out-of-range requests; never store unbounded floats. |
| **Acceptance test** | `POST /neuromod/adjust` with `dopamine=99.0` → stored state dopamine ≤ 0.8 (or 422). Same for negative values and for NE/ACh > 0.1. |
| **Wave** | W2 |

### DEBT-004 — Adaptive feedbacks saturate

| Field | Value |
|---|---|
| **Severity** | P1 |
| **Subsystem** | Neuromod |
| **Wave** | W2 |
| **Status** | **FIXED (W2)** |
| **Resolution (W2)** | Homeostatic law `m ← Π(m + η(δ − m))` in `AdaptiveParameter.update`; feedbacks are projected target levels. Acceptance: `TestHomeostaticLaw` — dopamine falls from peak on failure; 1000-update invariant. |
| **Proof** | `somabrain/adaptive/core.py:66-71`; `somabrain/admin/brain/neuromodulators.py:322-382` (mirrored at `runtime/neuromodulators.py:324-384`) |
| **What code does** | `AdaptiveParameter.update` does `current_value += learning_rate * delta` then clamps to `[min, max]`. All four feedback functions return **non-negative** quantities: DA = `success_rate + bias + boost` (`:332-336`), 5-HT = `1 - error_rate` (`:344`), NE = `min(NE_MAX, latency_term + urgency)` (`:363-366`), ACh = `accuracy * scale + memory_factor` (`:379-382`). Every parameter therefore only increases until it sticks at `max_value`. |
| **What docs claim** | `admin/brain/neuromodulators.py:241` calls this a "True learning neuromodulator system with adaptive parameters". |
| **REQUIRED FIX** | **FULL IMPLEMENT** signed error/PE-driven updates (e.g. `delta = f(target - current)` or a two-sided PE), or **DELETE** the adaptive layer if it is not the intended mechanism. Parameters must be able to decrease on adverse evidence. |
| **Acceptance test** | After N updates with `success_rate=1.0` then N updates with `success_rate=0.0`, dopamine must fall from its peak (today it stays at max). |
| **Wave** | W2 |

### DEBT-005 — ACh coupling vs comment vs Supervisor

| Field | Value |
|---|---|
| **Severity** | P1 |
| **Subsystem** | Neuromod |
| **Wave** | W2 |
| **Status** | **FIXED (W2)** |
| **Resolution (W2)** | ONE ACh law `acetylcholine_target(novelty, pred_error, memory_load)` shared by adaptive + Supervisor. Acceptance: `TestAChLaw::test_same_ach_delta_sign_as_supervisor`. |
| **Proof** | `somabrain/admin/brain/neuromodulators.py:369-382`; `somabrain/runtime/supervisor.py:135-136`, `:143`, `:156` |
| **What code does** | Adaptive path comment says "Higher acetylcholine for memory-intensive tasks" (`:372-373`) but the dominant term is `performance.accuracy * SOMABRAIN_NEURO_ACCURACY_SCALE` (scale default 0.05, `somabrain/settings/neuro.py:45-46`); `memory_factor` is added only when `task_type == "memory"` (`:374-377`, factor default 0.02). Supervisor comment says ACh responds to "novelty" and implements `raw_d_ach = g * novelty` (`:143`). Three distinct couplings for one variable. |
| **What docs claim** | `admin/brain/neuromodulators.py:12`: "Acetylcholine: Attention, focus, and memory consolidation". |
| **REQUIRED FIX** | **FULL IMPLEMENT** one documented ACh law used by every caller. Either drive ACh from attention demand (novelty/uncertainty) or from memory load — pick one, state it in the module docstring, and make adaptive + supervisor share it. |
| **Acceptance test** | Single property test over the chosen law: given the same `(performance, task_type, novelty, pred_error)`, adaptive update and supervisor `adjust` produce the same ACh delta sign. |
| **Wave** | W2 |

### DEBT-006 — Serotonin unused for control

| Field | Value |
|---|---|
| **Severity** | P2 |
| **Subsystem** | Neuromod |
| **Wave** | W2 |
| **Status** | **FIXED (W2)** |
| **Resolution (W2)** | 5-HT law `serotonin_target(pred_error)=1−pred_error`; consumer `AmygdalaSalience` gates (hysteresis·(1+5HT), soft T·(1+5HT)). Supervisor drives 5-HT. Acceptance: `TestSerotoninConsumer`. |
| **Proof** | `somabrain/runtime/supervisor.py:151`, `:154`; `somabrain/admin/brain/neuromodulators.py:339-344` |
| **What code does** | Supervisor explicitly holds serotonin constant ("serotonin unchanged in this proxy", `:151`) and copies the prior value (`:154`). The adaptive layer computes a 5-HT feedback (`:339-344`) and stores it, but no decision, threshold, gain, or retrieval path reads serotonin to change behaviour. Consumers are state, API (`api/endpoints/neuromod.py:40`, `:76`), and Prometheus (`metrics/neuromodulator.py:37-38`). |
| **What docs claim** | `admin/brain/neuromodulators.py:10`, `:18`: "Serotonin: Emotional stability and smoothing of neural responses" / "Serotonin: Provides emotional stability and response smoothing". |
| **REQUIRED FIX** | **DELETE** serotonin from the control surface (keep only if a consumer is implemented), or **FULL IMPLEMENT** the documented smoothing/threshold coupling and wire it into supervisor + cognition. |
| **Acceptance test** | If kept: a test showing a 5-HT change alters a documented downstream output (e.g. decision threshold). If deleted: `rg -n "serotonin" somabrain/ --type py` shows no control-path reads outside state/API/metrics. |
| **Wave** | W2 |

### DEBT-007 — Rust neuromod ODE is dead

| Field | Value |
|---|---|
| **Severity** | P1 |
| **Subsystem** | Neuromod / Rust core |
| **Wave** | W2 |
| **Status** | **FIXED (W2)** |
| **Resolution (W2)** | DELETED Rust `update`/`set_dynamics`/`get_dynamics` + `neuro_k_d_*`/`neuro_k_r_*`/`neuro_u_scale` keys. Rust is a state mirror. cargo test 14/14. Acceptance: `TestSupervisorWiring::test_rust_ode_deleted`. |
| **Proof** | `rust_core/src/neuro.rs:70-90` (ODE `dm/dt = k_d·x − k_r·m + bias + u_scale·u`); sole caller `scripts/verify_rust_migration.py:27` (`nm.update([0.5] * 4, [0.1] * 4, 0.1)`). Production Python only uses `set_state`/`get_state` (`admin/brain/neuromodulators.py:136-143`, `:148-155`; `runtime/neuromodulators.py:138-145`, `:150-155`). Dynamics constants `k_d`/`k_r`/`bias` are defined in `somabrain/brain_settings/models.py:454-520` and exposed via `set_dynamics`/`get_dynamics` (`neuro.rs:113-129`) but never loaded into a live ODE step. |
| **What docs claim** | `brain_settings/models.py:454` documents the ODE `dm/dt = k_d*x - k_r*m + bias + u_scale*u` as the neuromodulator dynamics. |
| **REQUIRED FIX** | **FULL IMPLEMENT** the ODE as the single neuromodulator update path (load `k_d`/`k_r`/`bias`/`u_scale` from brain_settings, step it from the cognitive loop), **or DELETE** `Neuromodulators.update`, `set_dynamics`, `get_dynamics`, and the brain_settings dynamics keys. |
| **Acceptance test** | If kept: production code path (not `scripts/`) invokes `update`; property test checks `dm/dt` formula against `brain_settings` constants. If deleted: `rg -n "fn update" rust_core/src/neuro.rs` returns nothing and no brain_settings dynamics keys remain. |
| **Wave** | W2 |

### DEBT-008 — Python vs Rust gains sign and magnitude mismatch

| Field | Value |
|---|---|
| **Severity** | P0 |
| **Subsystem** | Learning |
| **Wave** | W3 |
| **Proof** | Python: `somabrain/settings/cognitive.py:350-360` (`gain_alpha=1.0`, `gain_gamma=-0.5`, `gain_lambda=1.0`, `gain_mu=-0.25`, `gain_nu=-0.25`); `somabrain/learning/config.py:76-90` same defaults. Rust: `rust_core/src/adaptation.rs:118-122` (`gain_alpha=0.1`, `gain_gamma=0.05`, `gain_lambda=0.1`, `gain_mu=0.05`, `gain_nu=0.02`) — all positive. Update formulas are otherwise identical (`engine.py:369-386`; `adaptation.rs:169-179`). |
| **What code does** | On the same positive feedback, Python **decreases** γ/μ/ν (negative gains) while Rust **increases** them. Magnitudes also differ by ~10× for α/λ. The two engines cannot agree on a single step. |
| **What docs claim** | `LEARNING_MATHEMATICAL_PROOF.md:33` — "gain = direction and magnitude of update (can be positive or negative)"; the worked example at `:137` shows γ **increasing** on +1.0 reward (`0.1 → 0.1025`), which matches neither the settings default (−0.5 ⇒ decrease) nor Rust (+0.05 ⇒ increase by a different amount). |
| **REQUIRED FIX** | **FULL IMPLEMENT** one gains source (W1 contract module) consumed by both Python and Rust. Delete the independent Rust hardcodes. Signs and magnitudes must be identical. |
| **Acceptance test** | Cross-language parity test: same initial weights, gains, and 100 feedbacks ⇒ Python and Rust `get_retrieval`/`get_utility` match to 1e-12. Sign test: `gain_gamma < 0` and `signal > 0` ⇒ γ decreases in **both** engines. |
| **Wave** | W3 |

### DEBT-009 — Three τ mechanisms, four floors

| Field | Value |
|---|---|
| **Severity** | P1 |
| **Subsystem** | Learning |
| **Wave** | W3 |
| **Proof** | Mechanisms: (1) `apply_tau_annealing` `somabrain/learning/annealing.py:186-220` (linear/step multiplicative; **exp is a no-op per-feedback** at `:199-201`); (2) `apply_tau_decay` `:223-263` (multiplicative, hard floor `max(0.05, …)` at `:254`); (3) `check_entropy_cap` `:292-390` (reshapes τ with α/β/γ). Floors: `SOMABRAIN_TAU_MIN=0.4` `settings/cognitive.py:188`; `TAU_MIN_FLOOR=0.1` `:514`; decay hardcode `0.05` `annealing.py:254`; Rust `set_tau` clamp `[0.01, 10.0]` `rust_core/src/adaptation.rs:202`; engine inline clamp `0.01` `engine.py:572`. |
| **What code does** | Which floor applies depends on which of the three functions runs last and which settings namespace is loaded. Exponential annealing is configured as a mode (`settings/cognitive.py:336`) but does nothing per-feedback. |
| **What docs claim** | `LEARNING_MATHEMATICAL_PROOF.md:51` shows only `τ_{t+1} = max(τ_floor, τ_t × (1 - anneal_rate))` and uses `τ_floor = 0.01` at `:129-131`. `SOMABRAIN_MATHEMATICAL_PROOF_REPORT.md:155` publishes `floor ∈ [0.01, 0.1]`. |
| **REQUIRED FIX** | **FULL IMPLEMENT** a single τ schedule API with one floor constant and one anneal semantic (linear **or** exp **or** step — not three stacked). **DELETE** the unused branches and the extra floor literals. |
| **Acceptance test** | Property test: for any enabled schedule, τ is non-increasing and `τ ≥ τ_floor` where `τ_floor` is the single contract constant. `rg -n "max(0\\.05\|clamp(0\\.01\|TAU_MIN_FLOOR\|SOMABRAIN_TAU_MIN" somabrain/` shows one source. |
| **Wave** | W3 |

### DEBT-010 — Entropy cap rescales τ

| Field | Value |
|---|---|
| **Severity** | P1 |
| **Subsystem** | Learning |
| **Wave** | W3 |
| **Proof** | `somabrain/learning/annealing.py:315-370`, applied at `somabrain/learning/adaptation/engine.py:416-429` |
| **What code does** | `check_entropy_cap` treats `(α, β, γ, τ)` as a probability vector, sharpens non-dominant components, then rescales all four so they sum to `α+β+γ+τ` (`:363-370`). τ is a temperature, not a mixture weight; folding it into the entropy vector overwrites the annealed value from `apply_tau_annealing`/`apply_tau_decay` in the same call (`engine.py:402-429`). |
| **What docs claim** | `LEARNING_MATHEMATICAL_PROOF.md:183-207` claims entropy is `H = -Σ p_i log₂ p_i` with **softmax** `p_i = exp(w_i)/Σ exp(w_j)` (`:189`) and that learning reduces it. Code uses **linear** normalisation `probs = [v / s for v in vec]` (`annealing.py:321-322`). |
| **REQUIRED FIX** | **FULL IMPLEMENT** entropy cap over mixture weights only (α, β, γ — or the true mixture components). τ must not be an input to entropy sharpening. Align the entropy formula with the implementation. |
| **Acceptance test** | After `apply_tau_and_entropy`, τ equals the value produced by the schedule alone. Entropy property uses the implemented normalisation. |
| **Wave** | W3 |

### DEBT-011 — Wiener λ* formula vs default constant

| Field | Value |
|---|---|
| **Severity** | P0 |
| **Subsystem** | Mathcore |
| **Wave** | W3 |
| **Status** | **FIXED (W4)** |
| **Proof** | Formula: `rust_core/src/mathcore.rs` implements `λ* = Δ² / (12 p (1-p))` with `Δ = 2/(2^bits−1)`. Default: binder/unbind sites hardcoded `λ = (2/255)²/3` = λ*(p=0.5), and quantum unbind fell back to a third value `1e-4`. |
| **What code did** | Production binder/unbind used a constant valid only at p = 0.5 while the sparse encoder default is `SOMABRAIN_BHDC_SPARSITY = 0.1`. At p = 0.1 the formula gives `λ* ≈ 5.696e-5`. |
| **Resolution (W4)** | Single source `compute_wiener_lambda(p, bits)` (Rust + Python mirror). All defaults are `compute_wiener_lambda(production p, 8)`; callers may pass `p`. `gmd_lambda_reg` BrainSetting default is computed from the same formula. The hardcoded constants are deleted (`rg "2\\.05e-5" rust_core/ somabrain/` is empty). |
| **Acceptance test** | `PermutationBinder` default `lambda_reg` equals `compute_wiener_lambda(SOMABRAIN_BHDC_SPARSITY, 8)` within 1e-15 — covered by `tests/property/test_mathcore_wiener_fwht.py::TestWienerLambdaFormula`. |
| **Wave** | W3 → fixed in W4 |

### DEBT-012 — Theorem 1 p* ≥ 0.5 vs "p ≈ 0.1"

| Field | Value |
|---|---|
| **Severity** | P1 |
| **Subsystem** | Mathcore |
| **Wave** | W3 |
| **Status** | **FIXED (W4)** |
| **Proof** | `compute_optimal_p(delta) = (1 + sqrt(delta)) / 2`, which is **always ≥ 0.5** for δ ∈ (0, 1). Comment said "p* ≈ 0.1 recommended". |
| **What code did** | The function computed a quantity that never recommended the sparse p = 0.1 actually used by BHDC defaults. |
| **Resolution (W4)** | **DELETED** `compute_optimal_p` and the "p* ≈ 0.1" claim. `p = 0.1` is documented as an **engineering choice** (`PRODUCTION_SPARSITY_P`, `SOMABRAIN_BHDC_SPARSITY`), not a theorem. No fake theorem was introduced. |
| **Acceptance test** | No exported `compute_optimal_p` and no "p*" recommendation in code comments — verified by `cargo test` (no optimal-p test) and `rg "compute_optimal_p" rust_core/src somabrain/` empty outside historical docs. |
| **Wave** | W3 → fixed in W4 |

### DEBT-013 — Rust `BayesianMemory` test arity mismatch

| Field | Value |
|---|---|
| **Severity** | P0 |
| **Subsystem** | Mathcore / Rust tests |
| **Wave** | W3 |
| **Status** | **FIXED (W4)** |
| **Proof** | Constructor: `new(dimension, eta, lambda_reg)` — **3** parameters. Tests called it with **4** arguments and referenced a removed `compute_snr(p)` API. |
| **What code did** | `cargo test` could not compile the test module. |
| **Resolution (W4)** | Tests rewritten against the live API (`new(dimension, eta, lambda_reg)`, `compute_snr_at_lag`, `estimate_horizon`). Stale 4-arg calls and unfinished in-test commentary deleted. |
| **Acceptance test** | `cargo test` compiles and passes in `rust_core/` — 14/14 green. |
| **Wave** | W3 → fixed in W4 |

### DEBT-014 — Rust λ* unit test expects 2× implementation

| Field | Value |
|---|---|
| **Severity** | P0 |
| **Subsystem** | Mathcore / Rust tests |
| **Wave** | W3 |
| **Status** | **FIXED (W4)** |
| **Proof** | Implementation `λ* = (Δ²/12) / (p(1-p)) = Δ² / (12 p (1-p))`. Test expected `Δ² / (6 p (1-p))` — exactly twice the implementation. |
| **What code did** | The unit test expected exactly **twice** the value `compute_wiener_lambda` returns. |
| **Resolution (W4)** | Test pins the GMD definition `λ* = Δ² / (12 p (1-p))` exactly; factor-2 expectation deleted. `bits` is now honored (`Δ = 2/(2^bits−1)`). |
| **Acceptance test** | `cargo test test_wiener_lambda_theorem3` passes. Cross-check: `compute_wiener_lambda(0.1, 8) ≈ 5.695e-5`. |
| **Wave** | W3 → fixed in W4 |

### DEBT-015 — Python binder unbind is not Wiener

| Field | Value |
|---|---|
| **Severity** | P1 |
| **Subsystem** | Mathcore |
| **Wave** | W3 |
| **Status** | **FIXED (W4)** |
| **Proof** | `_PythonPermutationBinder.unbind` was `c_vec / denom` with a ±1e-12 floor; `lambda_reg` was stored and never used. Rust applied Wiener `v̂ = (c ⊙ π(b)) / (π(b)² + λ)`. `QuantumLayer.unbind_wiener` discarded its Wiener parameters and delegated. |
| **What code did** | When Rust was unavailable, unbind was exact division (numerically unstable on near-zero key elements) while the name and docs claimed Wiener-optimal unbinding. |
| **Resolution (W4)** | Python unbind is `(c ⊙ π(b)) / (π(b)² + λ*)` with `λ*` from `compute_wiener_lambda`, matching Rust (including optional FWHT mix and L2 norm). `unbind_wiener` now performs the Wiener rule and its unused parameters (`snr_db`, `k_est`, `alpha`, `whiten`) were deleted. |
| **Acceptance test** | `tests/property/test_mathcore_wiener_fwht.py::TestBindUnbindRoundTrip::test_python_unbind_is_wiener_rule` — Python unbind equals the Wiener formula to 1e-12. Zero-key-element case uses λ regularizer, not a 1e-12 floor. |
| **Wave** | W3 → fixed in W4 |

### DEBT-016 — Python FWHT / hadamard mix is a silent no-op

| Field | Value |
|---|---|
| **Severity** | P1 |
| **Subsystem** | Mathcore |
| **Wave** | W3 |
| **Status** | **FIXED (W4)** |
| **Proof** | `_PythonPermutationBinder` stored `self._mix` and accepted `mix="hadamard"` but `bind`/`unbind` never referenced it. Rust applied FWHT when `mix == "hadamard"`. |
| **What code did** | Python fallback silently ignored the hadamard mixing flag. Results differed from Rust with no error. |
| **Resolution (W4)** | Python fallback implements the same orthonormal FWHT as `mathcore.rs` and applies it in bind and unbind (H is self-inverse) when `mix == "hadamard"`. Non-2^r input raises `ValueError` in both languages (W4.4). |
| **Acceptance test** | `tests/property/test_mathcore_wiener_fwht.py::TestFwhtGuard` and round-trip tests with `mix="hadamard"` pass on both backends. No silent divergence. |
| **Wave** | W3 → fixed in W4 |

### DEBT-017 — Chebyshev spectral bounds are unexpanded

| Field | Value |
|---|---|
| **Severity** | P1 |
| **Subsystem** | Mathcore / Predictors |
| **Wave** | W3 |
| **Status** | **FIXED (W5b)** |
| **Proof** | `somabrain/math/graph_heat.py:31-34` took `(a, b) = estimate_spectral_interval(apply_A, n=x.shape[0], m=20)` and passed them straight into `chebyshev_heat_apply`. `estimate_spectral_interval` returns Ritz values of an m-step Lanczos tridiagonal (`somabrain/math/lanczos_chebyshev.py:47-54`) with **no safety expansion**. `chebyshev_heat_apply` maps A to `[-1, 1]` via `(2A - (b+a)I)/(b-a)` (`:87`) and evaluates the Chebyshev series. |
| **What code did** | Lanczos Ritz values need not contain the full spectrum. If a true eigenvalue lies outside `[a, b]`, the mapped operator leaves `[-1, 1]` and the Chebyshev approximation of `exp(-tA)` is unbounded. |
| **Resolution (W5b)** | **FULL IMPLEMENT** of `expand_spectral_interval(a, b) = (max(0, a−ε), b+ε)` with `SPECTRAL_INTERVAL_EPSILON = 0.1` (`somabrain/math/graph_heat.py:17-33`). `graph_heat_chebyshev` expands the Lanczos interval before the affine map (`:50-53`). Property tests import the same helper (`tests/property/test_predictor_properties.py:121,167,…`). |
| **Acceptance test** | `tests/property/test_memory_scoring_unify.py::TestChebyshevBoundsExpanded` — bounds are exactly `[a−ε, b+ε]` and the lower bound is floored at 0. `tests/property/test_predictor_properties.py` — `‖graph_heat_chebyshev(A, x, t) − expm(-t A) x‖ / ‖x‖ ≤ ε` with expanded bounds. |
| **Wave** | W3 → fixed in W5b |

### DEBT-018 — Rust "Mahalanobis" is Euclidean

| Field | Value |
|---|---|
| **Severity** | P1 |
| **Subsystem** | Predictors |
| **Wave** | W3 |
| **Status** | **FIXED (W4)** |
| **Proof** | `MahalanobisPredictor::distance` computed `sqrt(Σ (x_i - mean_i)²)`. The `covariance` field was `#[allow(dead_code)]` and never read or updated. |
| **What code did** | The type was named and exported as Mahalanobis but the metric was Euclidean L2 from the mean — no whitening by covariance. |
| **Resolution (W4)** | **FULL IMPLEMENT** of diagonal Mahalanobis: EWMA diagonal variance `σ²` (updated like the Python predictor), `distance = sqrt(Σ (x_i−μ_i)²/σ_i²)`. Name now equals the math. |
| **Acceptance test** | `tests/proofs/category_a/test_predictor_math.py` and `rust_core` unit tests: distance matches `sqrt((x−μ)ᵀ Σ⁻¹ (x−μ))` for diagonal Σ to 1e-10 on an anisotropic sample. |
| **Wave** | W3 → fixed in W4 |

### DEBT-019 — Rust SlowPredictor uses \|cos\|

| Field | Value |
|---|---|
| **Severity** | P1 |
| **Subsystem** | Predictors |
| **Wave** | W3 |
| **Status** | **FIXED (W4)** |
| **Proof** | Rust `error` used `1.0 - (dot / (norm_p * norm_a)).abs()`. Python canonical `cosine_error` is `clamp(1 - sim, 0, 1)` **without** absolute value. |
| **What code did** | Opposite vectors (cos = −1) yielded Rust error `1 - 1 = 0` (perfect match) instead of 1.0 (maximum error). |
| **Resolution (W4)** | **FULL IMPLEMENT** of `clamp(1 − cos, 0, 1)` in Rust. `.abs()` deleted. |
| **Acceptance test** | `tests/property/test_mathcore_wiener_fwht.py::TestCosineErrorFormula` — Rust and Python `cosine_error([1,0], [-1,0])` both return 1.0. |
| **Wave** | W3 → fixed in W4 |

### DEBT-020 — Recency: three formulas, conflicting scales

| Field | Value |
|---|---|
| **Severity** | P1 |
| **Subsystem** | Memory |
| **Wave** | W4 |
| **Status** | **FIXED (W5b)** |
| **Proof** | Formulas: (1) `compute_recency_features` `somabrain/memory/scoring.py:134-161` — `damp = exp(-(age/scale)^sharpness)`, `scale = SOMABRAIN_RECENCY_HALF_LIFE` (`:96`, default 60, `settings/cognitive.py:182`); (2) `UnifiedScorer._recency_component` `somabrain/admin/core/learning/scoring.py:119-131` — `exp(-age/τ)` with `SOMABRAIN_SCORER_RECENCY_TAU=32.0` (`settings/cognitive.py:175`); (3) WM salience `somabrain/memory/wm/wm_salience.py:172-175` and `wm_eviction.py:82-83` — `exp(-age/recency_scale)` with `SOMABRAIN_WM_RECENCY_TIME_SCALE`. Duplicated client formula: `somabrain/memory/client/ranking.py:244-261` (same shape as (1) but different config attribute names and defaults, `:213-220`). Scale conflicts for `SOMABRAIN_WM_RECENCY_TIME_SCALE`: `settings/cognitive.py:128-129` **default 1.0**; `settings/django_core.py:49` **default 60.0**; `bootstrap/core_singletons.py:48`, `:82` getattr fallback **3600**. |
| **What code did** | The same "recency" concept was three different kernels with three different time constants depending on call site. Changing one setting did not change the others. |
| **Resolution (W5b)** | **FULL IMPLEMENT** one kernel `stretched_exponential_recency` / `recency_features` in `somabrain/math/recency.py` (W1 contract constants `RECENCY_SCALE/SHARPNESS/FLOOR/CAP` in `somabrain/math/contracts.py`). Every live path imports it: `memory/scoring.py`, `memory/client/ranking.py`, `admin/core/learning/scoring.py`, `memory/wm/wm_salience.py`, `memory/wm/wm_eviction.py`, `memory/wm/core.py`, `context/builder.py`. One settings key `SOMABRAIN_WM_RECENCY_TIME_SCALE` (default `RECENCY_SCALE=60.0`); the `SCORER_RECENCY_TAU` path and the 3600/1.0 dual defaults are deleted. |
| **Acceptance test** | `tests/property/test_memory_scoring_unify.py::TestOneRecencyKernel` — one vector `(age=60, scale=60, sharpness=1.2, floor=0.05)` matches `exp(-1)` at the kernel, at `recency_features`, and at `UnifiedScorer._recency_component`. `rg -n "SOMABRAIN_WM_RECENCY_TIME_SCALE" somabrain/settings/` shows one default. |
| **Wave** | W4 → fixed in W5b |

### DEBT-021 — Two lexical-bonus formulas

| Field | Value |
|---|---|
| **Severity** | P1 |
| **Subsystem** | Memory |
| **Wave** | W4 |
| **Status** | **FIXED (W5b)** |
| **Proof** | `somabrain/memory/hit_processing.py:217-245` — token term `bonus = max(bonus, 0.3 + 0.1 * min(token_matches, 5))` (`:243-244`). `somabrain/memory/client/ranking.py:150-177` — token term `bonus += min(0.25 * token_matches, 1.0)` (`:175-176`). |
| **What code did** | Same name, same field list, different aggregation (`max` vs `+=`) and different coefficients (0.3+0.1·n vs 0.25·n). Recall ranking depended on which module ranked the hits. |
| **Resolution (W5b)** | **DELETE** the `hit_processing.py` formula entirely. One implementation `lexical_bonus` lives in `somabrain/memory/client/ranking.py:152-184` (the LIVE ranker per ARCH-TRUTH). `memory/scoring.py` and `memory/__init__.py` import that symbol. |
| **Acceptance test** | `tests/property/test_memory_scoring_unify.py::TestOneLexicalBonus` — fixed payload/query with 3 token matches returns `1.5 + 0.75` from the single function; `hit_processing.py` contains no second formula. |
| **Wave** | W4 → fixed in W5b |

### DEBT-022 — UnifiedScorer ignores constructor arguments

| Field | Value |
|---|---|
| **Severity** | P0 |
| **Subsystem** | Memory |
| **Wave** | W4 |
| **Status** | **FIXED (W5b)** |
| **Proof** | `somabrain/admin/core/learning/scoring.py:50-74`. Parameters `w_cosine`, `w_fd`, `w_recency`, `recency_tau` were accepted (`:53-58`) then discarded; values were re-read from settings via `_gain_setting` (`:64-67`). Factory passed explicit weights (`somabrain/bootstrap/singletons.py:232-239`) that had no effect. |
| **What code did** | Callers could not configure a scorer instance. Tests or tenants that constructed `UnifiedScorer(w_cosine=…, …)` got settings-global weights instead, with no warning. |
| **Resolution (W5b)** | **FULL IMPLEMENT** constructor arguments as the sole source of weights. The factory (`bootstrap/singletons.py:220-242`) reads settings and passes them in; the class never re-reads settings (`scoring.py:39-68`). `recency_tau` is gone — the recency component uses the canonical kernel with `recency_scale/sharpness/floor`. |
| **Acceptance test** | `tests/property/test_memory_scoring_unify.py::TestFdOffCeiling::test_constructor_weights_are_honored` — `UnifiedScorer(w_cosine=0.9, w_fd=0.0, w_recency=0.1, …).weights` is `0.9/0.0/0.1`, not the settings defaults. |
| **Wave** | W4 → fixed in W5b |

### DEBT-023 — FD-off score ceiling 0.75

| Field | Value |
|---|---|
| **Severity** | P1 |
| **Subsystem** | Memory |
| **Wave** | W4 |
| **Status** | **FIXED (W5b)** |
| **Proof** | Weights: `settings/cognitive.py:170-172` (`w_cosine=0.6`, `w_fd=0.25`, `w_recency=0.15`). When `fd_backend is None`, `_fd_component` returns 0.0 (`scoring.py:112-113`). Score was `w_cosine·cos + w_fd·fd + w_recency·rec` clamped to `[0, 1]` (`:159-164`). |
| **What code did** | With FD disabled, a perfect cosine match with full recency yielded `0.6 + 0 + 0.15 = 0.75`. The missing 0.25 was not redistributed. Ranking was compressed into the top 75% of the nominal scale. |
| **Resolution (W5b)** | **FULL IMPLEMENT** weight renormalisation over active components (`scoring.py:151-162`): terms are collected only for present backends, then divided by `active_weight`. With `fd_backend=None` and `age_seconds=0`, a unit vector scores `1.0`. |
| **Acceptance test** | `tests/property/test_memory_scoring_unify.py::TestFdOffCeiling` — identical unit vectors with `age_seconds=0` score 1.0 under default weights and under `0.9/0.0/0.1`. |
| **Wave** | W4 → fixed in W5b |

### DEBT-024 — Basal ganglia is the identity

| Field | Value |
|---|---|
| **Severity** | P1 |
| **Subsystem** | Cognition |
| **Wave** | W5 |
| **Proof** | `somabrain/admin/cognitive/basal_ganglia.py:52-68`: `return PolicyDecision(store=bool(store_gate), act=bool(act_gate))`. |
| **What code does** | The module header claims "action selection", "habit formation", "integration with salience and neuromodulator systems" (`:9-16`) but `decide` only casts two booleans. No thresholds, no competition, no neuromodulator input. |
| **What docs claim** | Same module docstring; `docs/SOMABRAIN_ARCHITECTURE.md` describes basal ganglia as the final decision component. |
| **REQUIRED FIX** | **FULL IMPLEMENT** action selection (thresholded utility / gated competition, with the neuromodulator inputs the header describes), **or DELETE** the module and the architectural claim. |
| **Acceptance test** | Two candidate actions with different utilities produce a non-trivial selection (not a pure pass-through of caller gates). |
| **Wave** | W5 |

### DEBT-025 — Prefrontal is a scalar gain

| Field | Value |
|---|---|
| **Severity** | P1 |
| **Subsystem** | Cognition |
| **Wave** | W5 |
| **Proof** | `somabrain/admin/cognitive/prefrontal.py:94-106`: dict numeric values are multiplied by `activation_threshold`; scalars multiplied by the same; other types unchanged. |
| **What code does** | "Executive control" is a single scalar multiply. No attention allocation, no conflict resolution, no working-memory gating — despite the docstring listing those roles (`:4-12`, `:49-51`). |
| **What docs claim** | `prefrontal.py:4-12` — "executive control functions … attention modulation". |
| **REQUIRED FIX** | **FULL IMPLEMENT** the executive functions the header lists (attention weights, conflict thresholding, WM gating) **or DELETE** the module and narrow the architecture description to what exists. |
| **Acceptance test** | A two-alternative input with conflicting evidence is resolved by the prefrontal policy, not by a uniform scale. |
| **Wave** | W5 |

### DEBT-026 — PersonalityStore.get raises NameError

| Field | Value |
|---|---|
| **Severity** | P0 |
| **Subsystem** | Cognition |
| **Wave** | W5 |
| **Status** | **FIXED (W5b)** |
| **Proof** | `somabrain/admin/cognitive/personality.py:25-36`. Parameter is `tenant` (`:25`); line `:36` is `return self._states.setdefault(t, PersonalityState())`. `t` is not defined in this scope. `set` and `update_traits` correctly use `tenant` (`:50`, `:64`). |
| **What code did** | Every `PersonalityStore.get(tenant)` call raised `NameError: name 't' is not defined`. The store was unreadable. |
| **Resolution (W5b)** | **FULL IMPLEMENT** the key as `tenant` on the `setdefault` line (`personality.py:36`). Empty tenant raises `ValueError` (no ambient fallback). |
| **Acceptance test** | `tests/property/test_memory_scoring_unify.py::TestPersonalityGet` — `PersonalityStore().get("acme")` returns a `PersonalityState`, a second call returns the same instance, and a different tenant gets a different instance. |
| **Wave** | W5 → fixed in W5b |

### DEBT-027 — LEARNING_MATHEMATICAL_PROOF.md contradicts code

| Field | Value |
|---|---|
| **Severity** | P0 |
| **Subsystem** | Docs |
| **Wave** | W6 |
| **Proof** | See table below. |
| **What code does** | Live formulas in `somabrain/learning/adaptation/engine.py:369-386`, `somabrain/learning/config.py:76-90`, `somabrain/settings/cognitive.py:188`, `somabrain/learning/annealing.py:321-322`. |
| **What docs claim** | `LEARNING_MATHEMATICAL_PROOF.md` as cited. |

| Doc claim (file:line) | Code reality (file:line) |
|---|---|
| `gain_α = 0.5 (from config)` (`LEARNING_MATHEMATICAL_PROOF.md:105`) | `SOMABRAIN_ADAPTATION_GAIN_ALPHA` default **1.0** (`settings/cognitive.py:350-351`) |
| γ increases on +reward: `0.1 → 0.1025` (`:137`) | `gain_gamma` default **−0.5** ⇒ γ **decreases** (`settings/cognitive.py:353-354`) |
| τ floor `max(0.01, …)` (`:128-131`) | `SOMABRAIN_TAU_MIN` default **0.4** (`settings/cognitive.py:188`); decay hardcode **0.05** (`annealing.py:254`) |
| Entropy `p_i = exp(w_i)/Σ exp(w_j)` softmax (`:189`) | Linear normalisation `v/sum(v)` (`annealing.py:321-322`) |
| "Proof by Exhaustive Testing" / "PASSED" (`:67-72`, `:175-176`, `:206`) | Worked numbers do not match production defaults; see DEBT-008 |

| **REQUIRED FIX** | **DELETE** the false proof content and **FULL IMPLEMENT** a proof document generated from the code formulas and production defaults after W1–W3 land. No claimed test that cannot be re-run against production symbols. |
| **Acceptance test** | Every numeric example in the rewritten document is reproduced by a committed test that imports production modules. Document register compliance check passes. |
| **Wave** | W6 |

### DEBT-028 — GMD / proof-report claims vs code

| Field | Value |
|---|---|
| **Severity** | P1 |
| **Subsystem** | Docs |
| **Wave** | W6 |
| **Proof** | `docs/SomabrainGMD.md:204-224` (λ* formula + p=0.1 value) vs the former hardcoded p=0.5-only binder constant — see DEBT-011. `docs/SomabrainGMD.md:260` recommends p = 0.1 while the former `compute_optimal_p` returned ≥ 0.5 — see DEBT-012. `SOMABRAIN_MATHEMATICAL_PROOF_REPORT.md:155` publishes τ `floor ∈ [0.01, 0.1]` against `SOMABRAIN_TAU_MIN=0.4` (`settings/cognitive.py:188`). |
| **What code does** | λ*/p*/README parts **RESOLVED in W4** (formula-only λ*, no `compute_optimal_p`, `rust_core/README.md` regenerated). τ floor conflict remains (DEBT-009). |
| **What docs claim** | GMD Theorem 3 numbers and Theorem 1 sparsity guidance as above; proof-report τ floor range. |
| **REQUIRED FIX** | **DELETE** numeric recommendations that do not match the implementation. Remaining for W6: GMD/proof-report regeneration around the single τ floor (λ* and p* already match code after W4). |
| **Acceptance test** | `scripts/check_docs.py` links each GMD numeric claim to a running symbol. `rg -n "2\\.05e-5" docs/ rust_core/ somabrain/` returns nothing after DEBT-011 — **held after W4**. |
| **Wave** | W6 |

---

## 4. Cross-cutting notes

### 4.1 Highest-priority unblockers (P0)

1. **DEBT-026** — one-token crash fix; can land immediately.
2. **DEBT-002 + DEBT-001** — learning currently cannot see adjusted neuromodulator state.
3. **DEBT-003** — unbounded neuromodulator writes.
4. **DEBT-008** — Python and Rust learning engines disagree on sign.
5. **DEBT-011 + DEBT-013 + DEBT-014** — mathcore constants and Rust tests.
6. **DEBT-022** — scorer configuration is ignored.
7. **DEBT-027** — proof document is actively wrong and must not be trusted by W1 design.

### 4.2 W1 contract surface (feeds every other wave)

The following single sources must exist before W2–W5 code changes, or the defects will reappear:

| Contract | Consumers today (examples) | Related debt |
|---|---|---|
| λ*(p) | `bhdc.rs`, `bhdc_encoder.py`, `quantum.py` | DEBT-011, DEBT-014, DEBT-015 |
| Adaptation gains (signed) | `learning/config.py`, `settings/cognitive.py`, `rust_core/src/adaptation.rs` | DEBT-008 |
| τ schedule + floor | `learning/annealing.py`, `adaptation.rs`, `settings/cognitive.py` | DEBT-009, DEBT-010 |
| Recency kernel + scale | `memory/scoring.py`, `memory/client/ranking.py`, `admin/core/learning/scoring.py`, `memory/wm/*` | DEBT-020 |
| Scorer weights | `admin/core/learning/scoring.py`, `bootstrap/singletons.py` | DEBT-022, DEBT-023 |
| Neuromodulator bounds + store | `api/endpoints/neuromod.py`, both neuromodulator trees, `rust_core/src/neuro.rs` | DEBT-001…007 |

### 4.3 Fix-mode rule (non-negotiable)

Every `REQUIRED FIX` above is either **DELETE** (remove the dead/false code or claim) or **FULL IMPLEMENT** (production-complete behaviour with tests). Intermediate tactics — wrappers that hide divergence, compatibility flags, silent fallbacks, or unfinished placeholders — are out of scope for this register and must not be used to close a row.

---

## 5. Traceability to waves

| Wave | Debt IDs | Exit criterion |
|---|---|---|
| **W1** | (enables 008, 009, 011, 020, 022) | Contract module exists; consumers import it; contract tests green in Python and Rust |
| **W2** | 001–007 (**all FIXED**) | One neuromodulator store; clamped API; adaptive parameters can decrease; ODE deleted; ACh/5-HT laws shared with real consumers |
| **W3** | 008–019 | `cargo test` green; gains parity; λ* from formula; binder FWHT/Wiener parity; predictor metrics honest |
| **W4** | 020–023 | One recency kernel; one lexical bonus; scorer constructor respected; FD-off score reaches 1.0 — **DONE (W5b)** |
| **W5** | 024–026 | Cognition modules either implement their stated role or are deleted with docs updated; personality store readable — **026 DONE (W5b)** |
| **W6** | 027–028 | Proof documents regenerated from code; every numeric claim test-backed |

---

*End of document — SOMA-BR-DEBT-001 v1.0.0*

---

## 6. Addendum — late revision close-out (2026-10-07)

| ID | Item | Status |
|---|---|---|
| ADD-01 | `X-Tenant-ID` partition authority | **FIXED** — credential-bound (`tenant.py`); header is assertion only |
| ADD-02 | `require_admin_auth` ≡ `require_auth` | **FIXED** — `SOMABRAIN_ADMIN_TOKEN` or JWT admin claim |
| ADD-03 | Homeostatic law test-only | **FIXED** — `eval_step` calls `adapt_from_performance` + `set_state` |
| ADD-04 | Outbox `dedupe_key` as event_id | **FIXED** — `enqueue_memory_event` returns PK |
| ADD-05 | `mark_events_for_replay` missing/wrong signature | **FIXED** — `db/outbox.py(event_ids)`; twins **DELETED** |
| ADD-06 | Constitution OPA fail-open | **FIXED** — deny on eval error |
| ADD-07 | Double recency / NaN→1.0 / s=1.0 | **FIXED** (W5c) |
| ADD-08 | Milvus `expr` injection | **FIXED** — tenant regex |
| ADD-09 | Universe filter fail-open | **FIXED** — missing tag ≠ match |
| ADD-10 | Fake SDR prefilter | **DELETED** |
| ADD-11 | `ports.json` client hijack | **DELETED** |
| ADD-12 | WM→LTM promotion async ORM | **FIXED** — `sync_to_async` |
| ADD-13 | Brain→SFM bearer 401 | **FIXED** — `memory/sfm_auth.resolve_sfm_api_token` fail-closed |
| ADD-14 | Replay twins dual impl | **DELETED** |
| ADD-15 | Live triad e2e gate | **FIXED (ClaudeCode GATE)** — LTM durable across restart; persisted_to_ltm=true |

**Totals addendum (ADD-01…ADD-15 only):** 15 of 15 addendum items closed (FIXED or DELETED). R-14 is closed. R-15 remains open only for the `somaAgent01` adapter call-site (outside this repo).

### 6.1 Post-GATE remaining (conversation quality — R-14 / R-15)

| ID | Item | Owner | Status |
|---|---|---|---|
| R-14 | Recall logs `no precomputed query vector`; query hash-embeds in another space so search misses durable LTM rows | ClaudeCode WAVE A / MiMoCode C2 | **CLOSED** — Brain ranking accepts `embedding=` and never re-embeds (C1/C3, spy-embedder proof). C2 ONE SPACE landed: `embed_text` is bit-identical to `TinyDeterministicEmbedder` (blake2b+fold+trigrams, golden fp match). Agent query vectors live in the brain's space. Live HTTP remember→recall gate PASS (score 1.0 exact hit). |
| R-15 | Fast-ack honesty | ClaudeCode WAVE A2 / MiMoCode contract+brain | **BRAIN + CONTRACT CLOSED** — `MemoryAck.from_brain_response` is the honest mapper (reads ok/durability/persisted_to_ltm/queued_for_ltm; never hardcodes ok=true; fails closed). Brain `/memory/remember` single path `ok=durable_accept`; batch `durable_accept`. Live response: `durability=persisted_ltm`, `persisted_to_ltm=true`. **Remaining outside somabrain:** `somaAgent01` `somabrain_adapter.remember` must call `from_brain_response` (ClaudeCode ACTIVE claim; OUTBOX posted). |

**Honest status:** ADD table closed. R-14 closed. R-15 closed on somabrain; adapter call-site is somaAgent01. Do not cite "FIXED 15/15" for the revision — that claim was withdrawn 2026-10-07.

