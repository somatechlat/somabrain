# SomaBrain — agent rules (always on)

## A2A (mandatory)
- Skill `a2a-coordination` is installed globally (`~/.claude/skills/a2a-coordination`).
- Channel: `docs/plans/a2a/` (INBOX, OUTBOX, LEDGER, CLAIMS) + `docs/plans/2026-10-05-COORDINATION-HANDOFF.md`.
- Before large edits: claim paths. After commits: log to LEDGER. ACK handoffs from other agents.
- CLI: `a2a status | claim | release | msg | ledger | handshake`.

## Non-negotiable
- NO SHIMS / FAKES / STUBS / TODOs. Delete or fully implement.
- Code is source of truth. Math must work. Docs match code.
- Branch `mimo-revision-0` for revision work; merge to `main` when done.
- No AI attribution on commits.

See `docs/VIBE_RULES.md`, `docs/THE-SOMA-COVENANT.md`, `AGENT.md`, `docs/iso/SOMA-BR-PLAN-MASTER-001.md`.
