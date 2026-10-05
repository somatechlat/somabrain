---
name: a2a-coordination
description: Agent-to-agent (A2A) coordination across coding agents on one machine (MiMoCode, Claude Code, Codex, Grok). Use when the user says "coordinate with the other agent", "A2A", "talk to the other Claude", "handoff", "multi-agent on this repo", "don't collide", or asks to message/claim files with another agent. Opens a file-based A2A channel (inbox/outbox/ledger/claims), optionally bridges via claude CLI, and enforces path claims so agents do not overwrite each other. Not for spawning MiMoCode subagents (use the actor tool) or for chat with end users.
---

# A2A Coordination

## Important
- **Never invent a remote A2A network.** On this machine A2A = files + optional local CLI bridge.
- **CODE IS SOURCE OF TRUTH.** Coordination docs must not lie about who owns what.
- **No shims/fakes/stubs** in any code you touch while coordinating.
- **Append-only** ledger/inbox/outbox. Do not delete others' messages.

## Instructions

### Step 1 — Locate or open the channel
Repo root: prefer the current workspace. Channel lives at:

```
docs/plans/2026-10-05-COORDINATION-HANDOFF.md   # or docs/plans/*COORDINATION*.md
docs/plans/a2a/INBOX.md
docs/plans/a2a/OUTBOX.md
docs/plans/a2a/LEDGER.md
docs/plans/a2a/CLAIMS.md
```

If missing, create them using `references/templates.md`. Protocol doc id: `SOMA-BR-COORD-A2A-001` when in somabrain.

### Step 2 — Discover the other agent
```bash
ps aux | grep -iE 'claude|codex|grok|mimo|droid' | grep -v grep
ls ~/.claude/projects/ 2>/dev/null
```
Record agent name, cwd, and tool (Claude Code / Codex / etc.).

### Step 3 — Handshake
1. Write a timestamped message to `INBOX.md` for the other agent.
2. If the other agent is **Claude Code**, bridge with a one-shot (no code edits):

```bash
cd <repo> && claude -p "Read docs/plans/<handoff>.md. Append ACK to docs/plans/a2a/LEDGER.md. List claims in CLAIMS.md. Do not change code this turn." --permission-mode acceptEdits --max-turns 8
```

3. Expect an ACK line in `LEDGER.md`. If no ACK in one attempt, leave the inbox message and tell the user — do not spam the CLI.

### Step 4 — Claim before edit
Append to `CLAIMS.md`:

`| path/prefix | agent-id | task-id | ISO timestamp | ACTIVE |`

Release with `RELEASED` when done. **Do not edit ACTIVE paths claimed by another agent** — request via `OUTBOX.md` instead.

### Step 5 — Log every commit
`| ISO timestamp | agent-id | COMMIT | sha + summary |`

### Step 6 — Resolve conflicts
1. Read `CLAIMS.md` + `LEDGER.md`.
2. File:line evidence beats memory.
3. Human Operator is final authority (Covenant Art 5).

## Examples
- User: "coordinate with the other agent on the repo" → open/find handoff, handshake, ACK in ledger.
- User: "tell Claude not to touch annealing.py" → INBOX message + CLAIMS row.
- User: "what did the other agent do?" → read LEDGER + git log.

## Troubleshooting
| Error | Cause | Fix |
|---|---|---|
| claude CLI auth fail | token/keys | `gh auth status`; user must auth |
| No ACK | agent busy / wrong cwd | leave INBOX; try `claude -p` from that agent's project dir |
| Merge conflict on a2a files | two appenders | keep both lines; never force-push |
| Other agent edits claimed paths | missing CLAIMS | send OUTBOX notice; Human gate |

## Bundled scripts
- `scripts/a2a.sh` — open channel, append message, handshake, status.
