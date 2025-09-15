#!/usr/bin/env bash
set -euo pipefail

ports=(9696 9797)
for p in "${ports[@]}"; do
  if lsof -ti tcp:"$p" >/dev/null 2>&1; then
    echo "Killing processes on port $p..."
    lsof -ti tcp:"$p" | xargs -r kill -9 || true
  else
    echo "No process listening on port $p"
  fi
done
echo "Done."
