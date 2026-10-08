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

## Local project agents (`.mimocode/agent/`)

| Agent | Use for |
|---|---|
| `brain-memory-engineer` | remember/recall/forget, outbox, ranking, SFM hop |
| `brain-adversarial-skeptic` | Every wave critic on memory/auth/neuromod |

## Partition

Do not edit `somaAgent01/webui/`. Claim paths before large edits.
