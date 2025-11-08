#!/bin/sh
set -eu

# Simple e2e smoke test used by Makefile.
# - POSTS a reward to the reward producer host port
# - Consumes from `cog.reward.events` inside the `somabrain_cog` container

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

exit 0
