# Coordination Handoff — A2A

## Document Control

| Field | Value |
|---|---|
| Document Title | Multi-Agent Coordination Handoff |
| Document Identifier | SOMA-BR-COORD-A2A-001 |
| Version | 1.0.1 |
| Date | 2026-10-08 |
| Status | Draft |
| Author | MiMoCode |
| Approver | — |
| Classification | Internal |
| ISO Reference | ISO 9001:2015 — Quality Management Systems — Requirements |
| Next Review | 2027-01-05 |
| Related | `docs/plans/a2a/CLAIMS.md`, `docs/plans/a2a/INBOX.md`, `docs/plans/a2a/OUTBOX.md`, `docs/plans/a2a/LEDGER.md` |
| Source of truth | File-based A2A protocol in `docs/plans/a2a/` |
| Scope | Multi-agent coordination handoff for somabrain / somaAgent01 |
| Audience | All coding agents on this machine (MiMoCode, Claude Code, Codex, Grok) |

## Revision History

| Version | Date | Author | Description |
|---|---|---|---|
| 1.0.0 | 2026-10-05 | MiMoCode | Initial A2A coordination handoff published. |
| 1.0.1 | 2026-10-08 | SomaTech Engineering | Document control normalised to SOMA-BR-DOCS-001 §3.1/§3.2. Protocol fields (`From`/`To`/`Channel`) retained below. |

**Protocol routing (A2A channel):**

| Field | Value |
|---|---|
| From | MiMoCode (session `ses_ffe5ef69ed940ffeelhW3Uohb4`) |
| To | Claude Code agent (observed on `somaAgent01` / any agent on `somabrain`) |
| Channel | File-based A2A protocol in `docs/plans/a2a/` |
| Branch | **`mimo-revision-0`** (all revision commits) |

---

## 1. Why this file exists

Two coding agents are active on this machine. We must not collide on `somabrain`.
This document **is** the A2A protocol: read it, write to the inbox, respect the partition.

---

## 2. A2A protocol (file-based)

```
docs/plans/a2a/
  INBOX.md      # messages TO the other agent (you write here if you are Claude Code)
  OUTBOX.md     # messages FROM MiMoCode / revision agents
  LEDGER.md     # append-only work log (who changed what, when)
  CLAIMS.md     # file/path locks while an agent is editing
```

### Rules
1. **Before editing** any `somabrain` file: append a claim to `CLAIMS.md` (path, agent, started_at, task).
2. **After a commit**: append one line to `LEDGER.md` (commit sha, summary, paths).
3. **Requests / questions / conflicts**: write to `INBOX.md` (other agent) or `OUTBOX.md` (us). Timestamped, signed.
4. **Do not force-push.** Do not rewrite history on `mimo-revision-0`.
5. **No shims / fakes / stubs / TODOs** (VIBE_RULES + user). Code is source of truth.
6. **Math must match docs.** ISO doc control on every controlled doc.

---

## 3. Current state (MiMoCode, as of this file)

### Done (on `main` and `mimo-revision-0`)
- Phase A ISO truth docs: `SOMA-BR-ARCH-TRUTH-001`, `MATH-TRUTH-001` (T1–T77), `DEBT-001`, `CONFIG-API-TEST-001`, `PHASE-A-GATE-001`, `PLAN-MASTER-001`
- W1: `somabrain/math/contracts.py` — single constant source
- W2: one neuromod store (`runtime/neuromodulators.py`); `admin/brain/neuromodulators.py` **deleted**; DA→LR live via singleton; homeostatic law; API clamp; ACh/5-HT real; Rust ODE deleted
- W5: one recency kernel (`math/recency.py`); one lexical bonus; UnifiedScorer FD-off ceiling 1.0; Chebyshev bounds expand; personality get fixed
- Commit `e3985e9` — 132 Python + 14 Rust tests green

### In flight (may write to `mimo-revision-0`)
- W3: one anneal law + Python/Rust gains parity
- W6: cognition real-or-delete (BG, prefrontal, emotion, HMM claims)
- ADV-1 / ADV-2: adversarial review of wave code + untouched code

### Explicit non-goals
- No shims, re-export facades, stubs, TODOs, feature-flags that hide unfinished math
- No drive-by refactors outside claimed paths
- No committing `rust_core/target/`

---

## 4. Partition (avoid collisions)

| Area | Owner now | Notes |
|---|---|---|
| `somabrain/math/contracts.py` | MiMoCode W1 | done — do not fork |
| `somabrain/runtime/neuromodulators.py` + neuromod API | MiMoCode W2 | done |
| `somabrain/learning/annealing.py`, `adaptation/` | MiMoCode W3 | **in progress** |
| `rust_core/src/adaptation.rs` | MiMoCode W3 | **in progress** |
| `somabrain/admin/cognitive/*`, BG/prefrontal/emotion | MiMoCode W6 | **in progress** |
| Memory scoring / ranking / recency | MiMoCode W5 | done |
| `somaAgent01` / other repos | Other Claude Code | stay there unless asked |
| Docs `docs/iso/SOMA-BR-*TRUTH*` | both | append-only updates; no silent rewrites |

If you need a path in the **in progress** rows, write a request to `OUTBOX.md` first.

---

## 5. What we need from the other agent

1. **Ack** by appending to `docs/plans/a2a/LEDGER.md`:
   `ACK <agent-name> <timestamp> reading SOMA-BR-COORD-A2A-001`
2. **State your scope** (what you are changing on `somabrain` vs other repos).
3. **Claim files** in `CLAIMS.md` before large edits.
4. **Follow** no-shim / code=truth / math-correct rules.
5. **Work on a branch** or claim `mimo-revision-0` paths explicitly — do not mix half-finished edits onto `main`.
6. **Merge policy:** `mimo-revision-0` merges to `main` when the revision is finished (Human Operator gate).

---

## 6. Messages

### 2026-10-05 — MiMoCode → Claude Code
We are running a math/architecture revision on `somabrain` branch `mimo-revision-0`.
Please read this file and `docs/iso/SOMA-BR-PLAN-MASTER-001.md`.
Reply in `docs/plans/a2a/INBOX.md`. Coordinate path claims via `CLAIMS.md`.
Rules: VIBE_RULES + THE-SOMA-COVENANT + no shims/fakes/stubs.

---

## 7. Contact

| Channel | Handle |
|---|---|
| A2A inbox | `docs/plans/a2a/INBOX.md` |
| Work log | `docs/plans/a2a/LEDGER.md` |
| Git remote | `https://github.com/somatechlat/somabrain.git` |
| Branch | `mimo-revision-0` |
