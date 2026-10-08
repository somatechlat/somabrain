# SOMA-BR-PHASE-A-GATE-001 — Phase A Exit Gate Review

**Gate outcome:** Phase A EXIT GATE: **PASS** (evidence in §2–4).

## Document Control

| Field | Value |
|---|---|
| Document Title | Phase A Exit Gate Review (DOC-A5) |
| Document Identifier | SOMA-BR-PHASE-A-GATE-001 |
| Version | 1.0.1 |
| Date | 2026-10-08 |
| Status | Approved |
| Author | SomaTech Engineering (DOC-A5 coordinator) |
| Approver | Engineering Lead |
| Classification | Internal |
| ISO Reference | ISO 9001:2015 — Quality Management Systems — Requirements |
| Next Review | 2027-01-04 |
| Source of truth | Code. This gate cross-checks the four truth documents against each other and against Phase A exit criteria in `SOMA-BR-PLAN-MASTER-001` §2. |
| Related | SOMA-BR-PLAN-MASTER-001 (Phase A exit criteria); inputs SOMA-BR-ARCH-TRUTH-001, SOMA-BR-MATH-TRUTH-001, SOMA-BR-DEBT-001, SOMA-BR-CONFIG-API-TEST-001 |
| Scope | Phase A documentation exit criteria and residual risks |

## Revision History

| Version | Date | Author | Description |
|---|---|---|---|
| 1.0.0 | 2026-10-04 | Engineering | Initial gate review. A1–A4 cross-check, exit criteria evidence, residual risks. |
| 1.0.1 | 2026-10-08 | SomaTech Engineering | Document control normalised to SOMA-BR-DOCS-001 §3.1/§3.2: `## Document Control` heading added, Status closed-set value `Approved` (gate PASS recorded above control table), house field names only. |

---

## 1. Deliverable completeness (DOC-A1…A4)

| ID | Deliverable | File | Lines | Status | Evidence |
|---|---|---|---|---|---|
| DOC-A1 | Architecture truth | `docs/iso/SOMA-BR-ARCH-TRUTH-001.md` | 286 | **COMPLETE** | Live/dead map, data flow, dual-implementation register, claims-vs-code |
| DOC-A2 | Math truth | `docs/iso/SOMA-BR-MATH-TRUTH-001.md` | 1203 | **COMPLETE** | Equations-as-implemented with file:line; false-claims appendix for legacy proof docs |
| DOC-A3 | Debt register | `docs/iso/SOMA-BR-DEBT-001.md` | 555 | **COMPLETE** | DEBT-001+ rows with file:line proof, severity, wave, acceptance tests |
| DOC-A4 | Config/API/testmap | `docs/iso/SOMA-BR-CONFIG-API-TEST-001.md` | 521 | **COMPLETE** | Config truth + DEF-01…14 duplicate register, API truth, VALID/TAUTOLOGY/XFAIL/MISSING testmap |
| DOC-A5 | This gate review | `docs/iso/SOMA-BR-PHASE-A-GATE-001.md` | — | **COMPLETE** | §2–4 below |
| DOC-A6 | False-claim archive | banners on proof reports | — | **COMPLETE** | `LEARNING_MATHEMATICAL_PROOF.md`, `SOMABRAIN_MATHEMATICAL_PROOF_REPORT.md` marked NON-AUTHORITATIVE (history preserved) |

---

## 2. Cross-document consistency check (A1 ↔ A2 ↔ A3 ↔ A4)

| Concept | A1 ARCH-TRUTH | A2 MATH-TRUTH | A3 DEBT-001 | A4 CONFIG-API-TEST | Verdict |
|---|---|---|---|---|---|
| Wiener λ* wrong vs formula | dual-impl register | λ* section + constants | DEBT-011 (P0, W3) | DEF-07 + §3.6 MISSING test | **CONSISTENT** |
| DA→LR wiring dead/no-op | live/dead map | N-equations / coupling | DEBT-002 (P0, W2) | §3.6 MISSING (engine.py:350-358) | **CONSISTENT** |
| `/neuromod/adjust` unclamped | API surface | — | DEBT-003 (P0, W2) | API-01 + §2.1 | **CONSISTENT** |
| Dual neuromod trees | dual-impl register | neuro module map | DEBT-001 (P1, W2) | §1.7 used-by both trees | **CONSISTENT** |
| τ floors / anneal split | — | one-τ truth | DEBT-009 (P1, W3) | DEF-05, DEF-06 | **CONSISTENT** |
| p* / quantizer contradiction | — | p* section | DEBT-012 (P1, W3) | (covered via λ*(p) MISSING) | **CONSISTENT** |
| Settings shadowing (WM defaults) | config notes | — | (see A4 DEF) | DEF-01, DEF-02 | **A4-only; feeds W1.2** |
| Test tautologies | — | — | (docs-sync W6) | TEST-01 + §3.1/3.5 | **A4-only; feeds W6** |
| Python binder ≠ Wiener | dual-impl | binder equations | (mathcore W3) | §3.5 WEAK Wiener test | **CONSISTENT** |
| Rust tests broken (arity, λ* 2×) | — | rust appendix | DEBT-013, DEBT-014 | — | **A2/A3-only** |

**Contradictions found between A1–A4: NONE.** Complementary coverage is intentional: A1 = structure, A2 = equations, A3 = defect proofs, A4 = config/API/test surface. ID spaces (DEBT-nnn vs DEF-nn vs X-n) map as in §3.

---

## 3. ID mapping (stable references for Phase B)

| A3 DEBT | A4 DEF / API | Prior audit X | Wave | Topic |
|---|---|---|---|---|
| DEBT-001 | — | — | W2 | Dual neuromod trees |
| DEBT-002 | §3.6 DA→LR | X4 | W2 | DA→LR no-op |
| DEBT-003 | API-01 | — | W2 | Unclamped neuromod API |
| DEBT-004 | — | X3 | W2 | Saturation / no homeostasis |
| DEBT-005 | — | X6 | W2 | ACh coupling inverted |
| DEBT-006 | — | — | W2 | Serotonin write-only |
| DEBT-007 | — | — | W2 | Rust ODE dead |
| DEBT-008 | — | X5 | W3 | Python/Rust gains drift |
| DEBT-009 | DEF-05, DEF-06 | X10-adj | W3 | τ floors / schedules |
| DEBT-010 | — | — | W3 | Entropy cap rewrites τ |
| DEBT-011 | DEF-07 | X2 | W3 | Wiener λ* |
| DEBT-012 | DEF-07 (related) | X1 | W3 | p* formula |
| DEBT-013 | — | X11 | W3 | Rust test arity |
| DEBT-014 | — | X11 | W3 | Rust λ* test 2× |
| (A4-only) | DEF-01…04, 08…14 | — | W1 | Settings duplicates / missing keys |
| (A4-only) | TEST-01, §3.6 | — | W1/W4/W6 | Tautologies + missing theorem tests |

---

## 4. Phase A exit criteria (from PLAN-MASTER §2)

| Criterion | Evidence | Met |
|---|---|---|
| Every major module labeled IMPLEMENTED / DEAD / TRIVIAL / BROKEN | ARCH-TRUTH-001 live/dead map | **YES** |
| Every math equation has file:line and live status | MATH-TRUTH-001 | **YES** |
| Every defect has proof and required fix (delete or full implement) | DEBT-001 rows + acceptance tests | **YES** |
| Config duplicate register complete | CONFIG-API-TEST-001 §1.9 DEF-01…DEF-14 | **YES** |
| Testmap: VALID / TAUTOLOGY / MISSING known | CONFIG-API-TEST-001 Part 3 + §3.6 | **YES** |
| **No code changes** in this phase | docs/ only; production `somabrain/` and `rust_core/` untouched | **YES** |

**Gate decision: Phase A EXIT = PASS.** Phase B (W1 contracts) may start.

---

## 5. Residual risks (do not block exit; track into Phase B)

| Risk | Owner wave | Note |
|---|---|---|
| DOCUMENT-REGISTER.md not yet regenerated to include the four truth docs + this gate | W1 / docs tooling | `scripts/gen_register.py` regenerates from `docs/` |
| DEF-* and DEBT-* ID spaces remain parallel until W1.2/W3 merge | W1 | §3 mapping is the bridge until then |
| Two proof reports still readable in-tree after A6 banners | W6 | Banners point to MATH-TRUTH; full rewrite is W6 |
| category_c / e2e tests remain env-gated (SOMA_INFRA_AVAILABLE) | W4/D | Gate review does not change skip conditions |

---

## 6. Authorization to proceed

Phase B Wave W1 (contracts: single math-contract source, kill duplicate settings, type `TRUTH_APPR_EPS`) is **unblocked**. Per binding rules: no shims, no fakes, delete-or-fully-implement only.

**End of document SOMA-BR-PHASE-A-GATE-001 Rev 1.0.0**
