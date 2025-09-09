#!/usr/bin/env sh
set -eu

HOST="${1:-127.0.0.1}"
PORT="${2:-9696}"
BASE="http://$HOST:$PORT"

echo "[seed] Seeding demo memories to $BASE ..."

hdrs="-H Content-Type:application/json"

seed_remember() {
  body="$1"
  curl -fsS -X POST "$BASE/remember" $hdrs -d "$body" >/dev/null || true
}

# Minimal demo payloads
seed_remember '{"coord": null, "payload": {"task":"write docs","importance":1,"memory_type":"episodic"}}'
seed_remember '{"coord": null, "payload": {"task":"gather examples","importance":1,"memory_type":"episodic"}}'
seed_remember '{"coord": null, "payload": {"task":"publish image","importance":1,"memory_type":"episodic"}}'

echo "[seed] Done. Try these commands:"
echo "curl -s $BASE/health"
echo "curl -s -X POST $BASE/recall -H 'Content-Type: application/json' -d '{\"query\":\"write docs\",\"top_k\":3}'"
echo "curl -s -X POST $BASE/plan/suggest -H 'Content-Type: application/json' -d '{\"task_key\":\"write docs\"}'"
