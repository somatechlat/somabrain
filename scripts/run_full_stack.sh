#!/usr/bin/env bash
set -euo pipefail

trap 'echo "[run_full_stack] Shutting down..."; (kill ${API_PID:-} 2>/dev/null || true)' EXIT

# Determine python interpreter (prefer project venv)
if [ -x ./.cleanup-venv/bin/python ]; then
  export PATH="$(pwd)/.cleanup-venv/bin:$PATH"
  PY_BIN="./.cleanup-venv/bin/python"
elif [ -x ./venv/bin/python ]; then
  export PATH="$(pwd)/venv/bin:$PATH"
  PY_BIN="./venv/bin/python"
else
  PY_BIN="python"
fi
echo "[run_full_stack] Using interpreter: $PY_BIN"

# Ensure memory endpoint is running on 9595
MEM_HEALTH="http://127.0.0.1:9595/health"
if ! curl -sf -m 0.5 "$MEM_HEALTH" >/dev/null 2>&1; then
  echo "[run_full_stack] ERROR: memory HTTP service not found on $MEM_HEALTH"
  echo "[run_full_stack] Start the shared infra stack (scripts/start_dev_infra.sh) or point SOMABRAIN_MEMORY_HTTP_ENDPOINT to an existing deployment."
  exit 90
fi

export SOMABRAIN_MEMORY_HTTP_ENDPOINT="http://127.0.0.1:9595"
export SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS=1
export SOMABRAIN_FORCE_FULL_STACK=1
export SOMABRAIN_REQUIRE_MEMORY=1
export SOMABRAIN_PREDICTOR_PROVIDER=mahal
export SOMABRAIN_RELAX_PREDICTOR_READY=1
export SOMABRAIN_MEMORY_ENABLE_WEIGHTING=1
export SOMABRAIN_MEMORY_PHASE_PRIORS="bootstrap:1.05,general:1.0,specialized:1.03"
export SOMABRAIN_MEMORY_QUALITY_EXP=1.0
export SOMABRAIN_DEFAULT_TENANT=sandbox
export SOMABRAIN_HOST=0.0.0.0
export SOMABRAIN_PORT=9696

# Start Somabrain API (foreground or background with smoke checks)
echo "[run_full_stack] Ensuring port 9696 free..."
if lsof -iTCP:9696 -sTCP:LISTEN -Pn >/dev/null 2>&1; then
  OLD_PID=$(lsof -t -iTCP:9696 -sTCP:LISTEN | head -n1 || true)
  if [ -n "$OLD_PID" ]; then
    echo "[run_full_stack] Killing existing process on 9696 (pid=$OLD_PID)"
    kill "$OLD_PID" || true
    for j in {1..10}; do
      if ! lsof -iTCP:9696 -sTCP:LISTEN -Pn >/dev/null 2>&1; then break; fi
      sleep 0.3
    done
    if lsof -iTCP:9696 -sTCP:LISTEN -Pn >/dev/null 2>&1; then
      echo "[run_full_stack] Force killing lingering process on 9696"
      kill -9 "$OLD_PID" || true
      sleep 0.5
    fi
  fi
fi
echo "[run_full_stack] Launching Somabrain API (uvicorn) on :9696"
$PY_BIN -m uvicorn somabrain.app:app --host 0.0.0.0 --port 9696 --log-level warning &
API_PID=$!

# Ensure OPA is running locally (host port defaults to 30004)
OPA_HP="${OPA_HOST_PORT:-30004}"
if ! curl -sf -m 0.4 "http://127.0.0.1:${OPA_HP}/health" >/dev/null 2>&1; then
  echo "[run_full_stack] ERROR: OPA server not reachable on http://127.0.0.1:${OPA_HP}/health"
  echo "[run_full_stack] Launch the real OPA deployment (e.g. via scripts/start_dev_infra.sh or Helm) before running the brain stack."
  exit 91
fi

# Wait for health ready
for i in {1..40}; do
  HJSON=$(curl -sf -m 1 http://127.0.0.1:9696/health || true)
  if [ -n "$HJSON" ]; then
    READY=$(printf '%s' "$HJSON" | python -c 'import sys,json;print(json.load(sys.stdin).get("ready"))' || echo "False")
    PRED=$(printf '%s' "$HJSON" | python -c 'import sys,json;print(json.load(sys.stdin).get("predictor_provider"))' || echo "?")
    EMBOK=$(printf '%s' "$HJSON" | python -c 'import sys,json;print("yes" if json.load(sys.stdin).get("embedder",{}).get("dim") else "no")' || echo "no")
    MEM_ITEMS=$(printf '%s' "$HJSON" | python -c 'import sys,json;print(json.load(sys.stdin).get("memory_items"))' || echo 0)
    if [ "$READY" = "True" ] || [ "$READY" = "true" ]; then
      echo "[run_full_stack] API ready. predictor=$PRED embedder_dim_ok=$EMBOK mem_items=$MEM_ITEMS"; break
    else
      if (( i % 5 == 0 )); then
        echo "[run_full_stack] waiting ($i) ready=$READY predictor=$PRED embedder_dim_ok=$EMBOK mem_items=$MEM_ITEMS"
      fi
    fi
  fi
  sleep 0.5
  if [ $i -eq 40 ]; then
    echo "[run_full_stack] ERROR: API did not become ready" >&2
    echo "$HJSON" >&2
    exit 1
  fi
done

# Smoke: remember & recall
echo "[run_full_stack] Performing smoke: remember"
curl -sf -X POST http://127.0.0.1:9696/remember -H 'Content-Type: application/json' \
  -d '{"coord_key":"smoke:1","payload":{"content":"smoke memory","phase":"bootstrap","quality_score":0.92}}' >/dev/null
sleep 0.3

echo "[run_full_stack] Performing smoke: recall"
RECALL=$(curl -sf -X POST http://127.0.0.1:9696/recall -H 'Content-Type: application/json' -d '{"query":"smoke","top_k":3}')
echo "[run_full_stack] Recall response: $RECALL"
if ! echo "$RECALL" | grep -qi 'smoke memory'; then
  echo "[run_full_stack] ERROR: Recall did not return stored memory" >&2
  exit 2
fi

echo "[run_full_stack] SUCCESS: Full stack operational (memory + API + weighting)."

# Persist an artifact to demonstrate writable area
ART_DIR="./artifacts/run"
mkdir -p "$ART_DIR"
echo "timestamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$ART_DIR/health_snapshot.env"
curl -sf http://127.0.0.1:9696/health > "$ART_DIR/health.json" || true
echo "[run_full_stack] Wrote artifacts: $(ls -1 $ART_DIR | tr '\n' ' ')"

echo "[run_full_stack] Final health JSON:" && cat "$ART_DIR/health.json" 2>/dev/null || echo "(missing)"
wait $API_PID
