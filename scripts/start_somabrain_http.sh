#!/usr/bin/env bash
set -euo pipefail

SB_ENDPOINT=${SOMABRAIN_MEMORY_HTTP_ENDPOINT:-http://localhost:9595}
export SOMABRAIN_MEMORY_MODE=http
export SOMABRAIN_MEMORY_HTTP_ENDPOINT="$SB_ENDPOINT"
export SOMABRAIN_MINIMAL_PUBLIC_API=0

logdir=${1:-.}
mkdir -p "$logdir"

PY_CAND=(".venv/bin/python" "python3")
for _p in "${PY_CAND[@]}"; do
  if [ -x "$_p" ]; then PY="$_p"; break; fi
done
PY=${PY:-python3}

echo "Starting SomaBrain on 9696 (HTTP -> $SB_ENDPOINT) using $PY"
nohup "$PY" -m uvicorn somabrain.app:app --host 0.0.0.0 --port 9696 >"$logdir"/somabrain-9696.log 2>&1 &
echo $! > /tmp/sb9696.pid

echo "Starting SomaBrain on 9797 (HTTP -> $SB_ENDPOINT) using $PY"
nohup "$PY" -m uvicorn somabrain.app:app --host 0.0.0.0 --port 9797 >"$logdir"/somabrain-9797.log 2>&1 &
echo $! > /tmp/sb9797.pid

echo "PIDs: 9696=$(cat /tmp/sb9696.pid), 9797=$(cat /tmp/sb9797.pid)"
echo "Logs in $logdir/somabrain-*.log"
