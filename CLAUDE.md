# somabrain — agent entry rules

| Field | Value |
|---|---|
| Primary standard | Shared triad rules: `../somaAgent01/docs/standards/SOMA-STD-TRIAD-001.md` (same stack, same rules) |
| A2A | `docs/plans/a2a/` — CLAIMS · INBOX · OUTBOX · LEDGER — **mandatory** |
| Handoff | `docs/plans/2026-10-05-COORDINATION-HANDOFF.md` |

## Stack lock (identical across triad)

FastAPI/Ninja (this service as deployed) · fail-closed memory · no shims · Vault secrets · Temporal for long work · one neuromod store · one layer vocabulary (wm/ltm/both).

## Memory

T-6 durable-before-hop. Idempotency key `mem:{coord}`. Never `return []` on outage.

## COGNITION ALWAYS ON — 100% FULL CAPACITY (HARD LAW)

SomaBrain **starts with every cognitive function ACTIVE at full capacity**. No default-OFF flags.

ON at boot and on the remember/recall path: hippocampus · amygdala · prefrontal · basal ganglia · neuromodulators · learner · planner · meta-brain · OAK · microcircuits · soft salience · drift monitor · SDR prefilter · graph augment · HRR-first · exec controller · memory weighting · entropy cap · dynamic LR · learning loop.

- Feature flags are **kill-switch / emergency-degrade only** — never to leave the brain half-thinking.
- Any code that returns empty results because a cog flag is off is a **DEFECT**.
- `{"plan": []}` when planner is disabled is a **LIE** — return `planner_disabled` with an explicit reason.
- Cognition runs on **every** memory cycle (remember, recall, promote), not only `/act`.
- Enforcement: `settings/cognitive.py` defaults, `runtime/modes.py` ModeConfig, `docs/VIBE_RULES.md`, and tests.

## Local project agents (`.mimocode/agent/`)

| Agent | Use for |
|---|---|
| `brain-memory-engineer` | remember/recall/forget, outbox, ranking, SFM hop |
| `brain-adversarial-skeptic` | Every wave critic on memory/auth/neuromod |

## Partition

Do not edit `somaAgent01/webui/`. Claim paths before large edits.
