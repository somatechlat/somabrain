# SomaBrain — Master Execution Plan

| Field | Value |
|---|---|
| Document Title | Master TODO, Waves, Rapid Development Methodology |
| Document Identifier | SOMA-BR-PLAN-MASTER-001 |
| Version | 1.0.0 |
| Date | 2026-10-04 |
| Status | Active |
| Author | SomaTech Engineering |
| Classification | Internal |
| Source of truth | **The code** (docs follow code) |

---

## 0. Binding rules (every agent, every wave)

1. **NO SHIMS. NO FAKES. NO BYPASSES. NO STUBS. NO MOCKS. NO PLACEHOLDERS. NO TODOs.**
2. **CODE IS SOURCE OF TRUTH.** Docs must match code. Papers/claims lose to code.
3. **MATH MUST BE PERFECTED SO SOMABRAIN WORKS.** Correctness of runtime behavior > theoretical claims.
4. **VIBE_RULES + SOMA-COVENANT** always. Real implementations. Full types. Django ORM + Milvus. Real infra verification.
5. **No production code before Phase A documentation exit** (except zero-risk doc sync).
6. **Agent fan-out package is mandatory** (rules + full file list + defect IDs + acceptance criteria).

---

## 1. Work structure

```
Phase A  DOCUMENT (now)     → full truth docs, zero behavior change
Phase B  MAKE MATH WORK     → waves W1–W6, real fixes only
Phase C  SYNC DOCS TO CODE  → regenerate truth docs from new code
Phase D  VERIFY ON REAL INFRA
```

---

## 2. Master TODO (complete)

### Phase A — Documentation (code = truth)

| ID | Deliverable | Agent | Status |
|---|---|---|---|
| DOC-A1 | `docs/iso/SOMA-BR-ARCH-TRUTH-001.md` — architecture, LIVE/DEAD, data flow | general-7 | running |
| DOC-A2 | `docs/iso/SOMA-BR-MATH-TRUTH-001.md` — equations as implemented | general-8 | running |
| DOC-A3 | `docs/iso/SOMA-BR-DEBT-001.md` — defect register with proofs | general-9 | running |
| DOC-A4 | `docs/iso/SOMA-BR-CONFIG-API-TEST-001.md` — config/API/testmap | general-10 | running |
| DOC-A5 | Gate review: cross-check A1–A4 for contradictions | coordinator | after A1–A4 |
| DOC-A6 | Archive false claims: mark proof docs WRONG (no deletion of history) | after A5 | |

**Phase A exit criteria**
- [ ] Every major module labeled IMPLEMENTED / DEAD / TRIVIAL / BROKEN
- [ ] Every math equation has file:line and live status
- [ ] Every defect has proof and required fix (delete or full implement)
- [ ] Config duplicate register complete
- [ ] Testmap: VALID / TAUTOLOGY / MISSING known
- [ ] **No code changes** in this phase

### Phase B — Waves (make it work)

#### Wave W1 — Contracts (foundation)
| ID | Todo | Fix mode | Done when |
|---|---|---|---|
| W1.1 | Single math-contract source for λ*(p), gains, τ, recency, bounds, D, p | one real module | all consumers import it; `cargo`/pytest contract tests |
| W1.2 | Kill duplicate settings (τ floors, recency scale, CHEB_K names) | one key each | CONFIG table has one row per concept |
| W1.3 | Type `TRUTH_APPR_EPS` as float | real fix | no str comparison |

#### Wave W2 — Neuromodulation (make live)
| ID | Todo | Fix mode | Done when |
|---|---|---|---|
| W2.1 | One neuromod module; delete the other tree | **DELETE** duplicate | single import path |
| W2.2 | Learner uses singleton for dopamine | real wiring | test: d change ⇒ lr_scale change |
| W2.3 | Homeostatic update law (mean-reverting) | **replace** saturating integrator | stationary mean under zero-mean noise |
| W2.4 | Clamp API to \(\mathcal{M}\) | real validation | out-of-range rejected |
| W2.5 | ACh coupling matches stated intent | real math | comment = code |
| W2.6 | Serotonin wired to a real consumer **or removed** | full implement or delete | no write-only state |
| W2.7 | Delete or wire Rust ODE + supervisor | wire or **delete** | zero dead writers |

#### Wave W3 — Learning + annealing
| ID | Todo | Fix mode | Done when |
|---|---|---|---|
| W3.1 | One τ law + one floor | delete extras | one implementation |
| W3.2 | Gains identical Python/Rust | contract | drift test green |
| W3.3 | Entropy cap excludes τ or one mass rule | real math | no fighting annealer |
| W3.4 | Scorer weights honest (renormalize if FD off) | real math | max score = 1 |
| W3.5 | DA→LR real (depends W2.2) | wiring | non-constant scale |

#### Wave W4 — Math core / BHDC
| ID | Todo | Fix mode | Done when |
|---|---|---|---|
| W4.1 | λ* from formula at production p | real constant | matches E9 |
| W4.2 | Theorem 1: fix or remove false p* | truth | no contradiction |
| W4.3 | Python unbind = Wiener | real algorithm | same as Rust |
| W4.4 | FWHT errors on non-2^r | real error | no silent wrong |
| W4.5 | Rust tests compile and pin theorems | real tests | `cargo test` green |
| W4.6 | Cosine error identical both languages | one formula | drift test |
| W4.7 | Mahalanobis real or renamed | implement or rename | name = math |

#### Wave W5 — Memory + predictors
| ID | Todo | Fix mode | Done when |
|---|---|---|---|
| W5.1 | One recency family + one time scale | delete extras | one formula |
| W5.2 | One lexical bonus | delete copy | one formula |
| W5.3 | Chebyshev bounds margin in production | real fix | matches tests |
| W5.4 | Property tests call production code | rewrite tests | zero local re-impls |

#### Wave W6 — Cognition honesty
| ID | Todo | Fix mode | Done when |
|---|---|---|---|
| W6.1 | Basal ganglia: real selection **or delete** | full or delete | name = math |
| W6.2 | Prefrontal: real gating **or delete** | full or delete | no fake free energy |
| W6.3 | Emotion: real coupling **or delete** | full or delete | no orphan state |
| W6.4 | Personality bug + real coupling **or delete** | full or delete | works or gone |
| W6.5 | HMM params: document fixed **or** implement online EM | truth or full | no false learning claim |

### Phase C — Docs sync
| ID | Todo |
|---|---|
| C.1 | Regenerate MATH-TRUTH / ARCH-TRUTH / CONFIG from new code |
| C.2 | Rewrite or delete false proof reports to match (L3) reality |
| C.3 | TESTMAP: every live theorem has production test |
| C.4 | GMD/README match implementation (quantizer, λ*, p*, APIs) |

### Phase D — Real verification
| ID | Todo |
|---|---|
| D.1 | Golden recall dataset |
| D.2 | Live neuromod integration (real store) |
| D.3 | Cross-language contract suite |
| D.4 | Real infra smoke (Covenant Art 24) |

---

## 3. Waves & dependencies (rapid)

```
        [Phase A docs: A1 A2 A3 A4]     ← PARALLEL NOW
                    |
                    v
        [A5 gate review]
                    |
        +-----------+-----------+
        v           v           v
       W1          W4          W5     ← PARALLEL (no interdep)
        |           |           |
        v           |           |
       W2           |           |
        |           |           |
        v           v           v
       W3          W6 (after W2 for neuromod naming)
                    |
                    v
              Phase C docs sync
                    |
                    v
              Phase D verify
```

**W1 must complete before W2/W3** (contracts feed neuromod and learning).  
**W4, W5 parallel with W1–W2.**  
**W6 after W2** (naming/claims depend on real neuromod).

---

## 4. Rapid development methodology

### 4.1 Work package (every agent, every task)

```
1. RULES block (shim/fake/bypass ban, code=truth, math must work)
2. CONTEXT: repo paths, exact files, LIVE/DEAD, DEBT-IDs, equation IDs
3. SCOPE: what to change (or document) — nothing else
4. FIX MODE: DELETE | FULL IMPLEMENT | REWRITE DOCS TO CODE  (never shim)
5. ACCEPTANCE: tests + doc sync + no new debt
6. FORBIDDEN: extra files, refactors outside scope, new abstractions
```

### 4.2 PR / change discipline

- One DEBT-ID (or DOC-A-ID) per PR when possible
- Same PR: code + tests + docs so they never drift
- Cite DEBT-xxx and equations in the description
- CI must be green before merge
- **No "fix later"** — incomplete work stays open, never faked done

### 4.3 Coordination protocol

| Event | Action |
|---|---|
| Agent spawn | Full work package injected |
| Agent blocked | Report block; do not invent |
| Wave start | Coordinator confirms W-dependencies clear |
| Wave end | Checklist against DEBT rows + tests |
| Contradiction between agents | **Code wins**; re-read file:line; update docs |

### 4.4 Anti-drift rules for agents

1. Before writing: re-read the exact function (file:line).  
2. Never copy equations from proof docs — extract from code.  
3. Never add `# TODO`, `pass`, `NotImplementedError` for product paths.  
4. Never create compatibility aliases.  
5. If two implementations exist: one becomes THE implementation; the other is deleted.  
6. If a name lies (Mahalanobis, free energy, RPE): rename or implement the real thing.  
7. Docs updated in the same change as code.

### 4.5 Definition of Done (global)

- System **works** (live paths real and tested)
- Math **correct** (equations match running code)
- Docs **true** (ISO-style structure, zero false claims)
- **Zero** shims/fakes/stubs/bypasses
- Defect register empty for P0/P1 or explicitly accepted by Human Operator

---

## 5. Agent roster (this session)

| Agent | Package | Output |
|---|---|---|
| general-7 | DOC-A1 architecture truth | ARCH-TRUTH-001 |
| general-8 | DOC-A2 math truth | MATH-TRUTH-001 |
| general-9 | DOC-A3 debt register | DEBT-001 |
| general-10 | DOC-A4 config/API/testmap | CONFIG-API-TEST-001 |
| next wave | W1–W6 packages from §2 | real fixes |

---

## 6. Immediate next actions

1. A1–A4 agents finish truth docs (running).  
2. Coordinator A5: merge findings, freeze DEBT list.  
3. Spawn W1 (contracts) with DEBT rows + MATH-TRUTH constants table.  
4. Parallel W4 + W5.  
5. W2 → W3 → W6.  
6. Phase C sync, Phase D verify.

**Human Operator gate:** after A5, confirm DEBT P0 list before any Phase B code.
