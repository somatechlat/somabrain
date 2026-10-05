#!/usr/bin/env bash
# A2A coordination helper — file-based protocol + optional Claude Code bridge.
set -euo pipefail

ROOT="${A2A_ROOT:-$(pwd)}"
A2A="$ROOT/docs/plans/a2a"
HANDOFF="$ROOT/docs/plans/2026-10-05-COORDINATION-HANDOFF.md"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
AGENT="${A2A_AGENT:-MiMoCode}"

usage() {
  cat <<'EOF'
Usage: a2a.sh <command> [args]

Commands:
  init                 Create channel files if missing
  status               Show claims + last ledger lines
  msg <from> <to> <text>   Append message to INBOX.md
  out <text>           Append to OUTBOX.md as A2A_AGENT
  claim <path> <task>  Claim a path
  release <path>       Release a claim
  ledger <action> <detail>  Append ledger row
  handshake            Bridge to local claude CLI (if present)
  discover             List local coding-agent processes
EOF
}

cmd="${1:-status}"
shift || true

case "$cmd" in
  init)
    mkdir -p "$A2A"
    for f in INBOX.md OUTBOX.md LEDGER.md CLAIMS.md; do
      [ -f "$A2A/$f" ] || printf '# A2A %s\n' "$f" >"$A2A/$f"
    done
    echo "A2A channel ready at $A2A"
    ;;
  status)
    echo "=== CLAIMS ==="; cat "$A2A/CLAIMS.md" 2>/dev/null | tail -20
    echo "=== LEDGER (last 15) ==="; cat "$A2A/LEDGER.md" 2>/dev/null | tail -15
    echo "=== INBOX (last 10) ==="; cat "$A2A/INBOX.md" 2>/dev/null | tail -10
    ;;
  msg)
    from="${1:?from}"; to="${2:?to}"; text="${3:?text}"
    printf '\n## [%s] FROM %s TO %s\n\n%s\n' "$TS" "$from" "$to" "$text" >>"$A2A/INBOX.md"
    echo "INBOX += $from → $to"
    ;;
  out)
    text="${1:?text}"
    printf '\n## [%s] FROM %s\n\n%s\n' "$TS" "$AGENT" "$text" >>"$A2A/OUTBOX.md"
    echo "OUTBOX updated"
    ;;
  claim)
    path="${1:?path}"; task="${2:?task}"
    printf '| %s | %s | %s | %s | ACTIVE |\n' "$path" "$AGENT" "$task" "$TS" >>"$A2A/CLAIMS.md"
    echo "CLAIMED $path"
    ;;
  release)
    path="${1:?path}"
    printf '| %s | %s | — | %s | RELEASED |\n' "$path" "$AGENT" "$TS" >>"$A2A/CLAIMS.md"
    echo "RELEASED $path"
    ;;
  ledger)
    action="${1:?action}"; detail="${2:?detail}"
    printf '| %s | %s | %s | %s |\n' "$TS" "$AGENT" "$action" "$detail" >>"$A2A/LEDGER.md"
    echo "LEDGER += $action"
    ;;
  handshake)
    if [ ! -f "$HANDOFF" ]; then
      echo "No handoff at $HANDOFF" >&2
      exit 1
    fi
    if ! command -v claude >/dev/null 2>&1; then
      echo "claude CLI not found — leave message in INBOX.md" >&2
      exit 2
    fi
    (cd "$ROOT" && claude -p "Read docs/plans/2026-10-05-COORDINATION-HANDOFF.md. Append ACK to docs/plans/a2a/LEDGER.md using this exact format: | $(date -u +%Y-%m-%dT%H:%M:%SZ) | ClaudeCode | ACK | reading SOMA-BR-COORD-A2A-001 |. If you edit somabrain paths, list them in docs/plans/a2a/CLAIMS.md. Do not change code this turn." --permission-mode acceptEdits --max-turns 8)
    ;;
  discover)
    ps aux | grep -iE 'claude|codex|grok|mimo|droid' | grep -v grep || true
    ;;
  *)
    usage; exit 1
    ;;
esac
