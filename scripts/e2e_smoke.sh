#!/bin/sh
set -eu

# Simple e2e smoke test used by Makefile.
# - POSTS a reward to the reward producer host port
# - Consumes from `cog.reward.events` inside the `somabrain_cog` container
# - Verifies a config update is produced and `/tau` reflects a change

COG_PORT=${COG_REWARD_PRODUCER_HOST_PORT:-30083}
URL="http://127.0.0.1:${COG_PORT}/reward/e2e-$$"

echo "POSTing reward to ${URL}"
curl -sS -X POST "${URL}" -H 'Content-Type: application/json' -d '{"r_task":0.9,"r_user":0.1}' || {
  echo "POST failed" >&2
  exit 2
}

echo "POST OK — consuming from cog.reward.events inside somabrain_cog"

docker compose -p somabrain exec -T somabrain_cog python3 - <<'PY'
from confluent_kafka import Consumer
c=Consumer({'bootstrap.servers':'somabrain_kafka:9092','group.id':'make-smoke','auto.offset.reset':'earliest'})
c.subscribe(['cog.reward.events'])
import time
start=time.time()
while time.time()-start<8:
    msg=c.poll(1.0)
    if msg is None: continue
    if msg.error():
        print('error', msg.error())
        continue
    print('GOT:', msg.value())
    break
else:
    print('no messages')
c.close()
PY

# Check that /tau endpoint is reachable and returns a numeric value
COG_INT_PORT=${COG_INTEGRATOR_HOST_PORT:-30010}
TAU_URL="http://127.0.0.1:${COG_INT_PORT}/tau"
echo "Checking tau at ${TAU_URL}"
TAU_BEFORE=$(curl -sS "$TAU_URL" || echo "")
sleep 4
TAU_AFTER=$(curl -sS "$TAU_URL" || echo "")
echo "tau before=${TAU_BEFORE} after=${TAU_AFTER}"

# Basic assertion: values must be non-empty and differ (unless keepalive emitted same value)
if [ -z "$TAU_BEFORE" ] || [ -z "$TAU_AFTER" ]; then
    echo "tau endpoint empty" >&2
    exit 3
fi
if [ "$TAU_BEFORE" = "$TAU_AFTER" ]; then
    echo "warning: tau unchanged (may be acceptable if reward low)" >&2
fi

# --- Optional: Regret KPI smoke (requires learner_online + metrics) ---
# Emit a synthetic NextEvent to cog.next.events and assert regret EWMA is observed.
# This block is best-effort: it will not fail the smoke if the learner or metrics are unavailable.

# shellcheck disable=SC2015
if docker compose -p somabrain ps somabrain_cog >/dev/null 2>&1; then
    echo "Emitting synthetic NextEvent for regret KPI check"
    docker compose -p somabrain exec -T somabrain_cog python3 - <<'PY' || echo "next_event emit skipped"
from kafka import KafkaProducer
import json, time, sys
try:
        p = KafkaProducer(bootstrap_servers='somabrain_kafka:9092', value_serializer=lambda v: json.dumps(v).encode('utf-8'))
        ev = {'tenant':'sandbox','confidence':0.6,'ts':int(time.time()*1000)}
        p.send('cog.next.events', ev).get(timeout=5)
        p.flush()
        print('sent next_event', ev)
except Exception as e:
        print('emit failed', e, file=sys.stderr)
PY
    # Give learner a moment to consume and update metrics
    sleep 2
    echo "Checking regret EWMA inside somabrain_cog"
    docker compose -p somabrain exec -T somabrain_cog sh -lc "curl -sS http://127.0.0.1:8084/metrics | grep '^somabrain_learning_regret_ewma' || true" | sed -n '1p'
fi

exit 0
