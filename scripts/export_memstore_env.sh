#!/usr/bin/env bash
set -euo pipefail
# export_memstore_env.sh
# Extract the Memory HTTP endpoint and token from the current stack env-file
# and write a host-friendly export file you can "source" to run host tools.

ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"

ENVFILE=".env"
OUTFILE="scripts/.memstore.env"

if [[ ! -f "$ENVFILE" ]]; then
  echo "[export_memstore_env] Missing $ENVFILE. Run scripts/dev_up_9999.sh or scripts/dev_up.sh first." >&2
  exit 1
fi

# Read values from .env (last assignment wins)
MEM_ENDPOINT=$(grep -E '^SOMABRAIN_MEMORY_HTTP_ENDPOINT=' "$ENVFILE" | tail -n1 | cut -d= -f2- || true)
# Prefer any token already present in the current shell, otherwise read from .env
MEM_TOKEN=${SOMABRAIN_MEMORY_HTTP_TOKEN:-$(grep -E '^SOMABRAIN_MEMORY_HTTP_TOKEN=' "$ENVFILE" | tail -n1 | cut -d= -f2- || true)}

# Fallbacks if not present
MEM_ENDPOINT=${MEM_ENDPOINT:-http://127.0.0.1:9595}

# For host use, prefer 127.0.0.1 over host.docker.internal
MEM_ENDPOINT_HOST=$MEM_ENDPOINT
if [[ "$MEM_ENDPOINT_HOST" == http://host.docker.internal:* ]]; then
  MEM_ENDPOINT_HOST=${MEM_ENDPOINT_HOST/host.docker.internal/127.0.0.1}
fi

mkdir -p scripts
cat > "$OUTFILE" <<EOF
export SOMABRAIN_MEMORY_HTTP_ENDPOINT="$MEM_ENDPOINT_HOST"
export SOMABRAIN_MEMORY_HTTP_TOKEN="${MEM_TOKEN:-}"
EOF

echo "[export_memstore_env] Wrote $OUTFILE"
echo "  SOMABRAIN_MEMORY_HTTP_ENDPOINT=$MEM_ENDPOINT_HOST"
if [[ -n "${MEM_TOKEN:-}" ]]; then
  echo "  SOMABRAIN_MEMORY_HTTP_TOKEN set (length ${#MEM_TOKEN})"
else
  echo "  SOMABRAIN_MEMORY_HTTP_TOKEN is empty"
fi

# Quick auth probe: treat 200/404/422 as OK for token presence; 401/403 as auth failure
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -H "Content-Type: application/json" \
  ${MEM_TOKEN:+-H "Authorization: Bearer $MEM_TOKEN"} \
  -X POST "$MEM_ENDPOINT_HOST/memories/search" --data '{"query":"auth_probe","top_k":1}') || STATUS=000

case "$STATUS" in
  200|404|422)
    echo "[export_memstore_env] Auth probe OK (status $STATUS)."
    ;;
  401|403)
    echo "[export_memstore_env] Auth probe FAILED (status $STATUS). Token may be missing or invalid for $MEM_ENDPOINT_HOST." >&2
    ;;
  000)
    echo "[export_memstore_env] Unable to reach $MEM_ENDPOINT_HOST. Is the memory service listening on port 9595?" >&2
    ;;
  *)
    echo "[export_memstore_env] Probe returned status $STATUS (informational).";
    ;;
esac

echo
echo "Usage:"
echo "  source $OUTFILE"
echo "  python benchmarks/adaptation_learning_bench.py --memstore-url \"$MEM_ENDPOINT_HOST\" --seed-memstore 1000 --iterations 300 --plot"
