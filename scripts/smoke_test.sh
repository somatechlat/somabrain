#!/usr/bin/env bash
set -euo pipefail

MSG="smoke-$(date +%s)"

echo "[smoke] Message ID: $MSG"

echo "[smoke] Producing to Kafka (test-topic)..."
# use docker exec with an inner bash so quoting is handled inside the container
docker exec -i sb_kafka bash -c "printf '%s\n' \"$MSG\" | kafka-console-producer.sh --bootstrap-server localhost:9092 --topic test-topic" || echo "[smoke] Kafka produce failed"

echo "[smoke] Consuming one message from Kafka (may be from beginning)..."
docker exec sb_kafka kafka-console-consumer.sh --bootstrap-server localhost:9092 --topic test-topic --from-beginning --max-messages 1 --timeout-ms 5000 || true

echo "[smoke] Redis set/get test..."
redis-cli -u redis://localhost:6379 SET smoke_test_key "$MSG" >/dev/null
VAL=$(redis-cli -u redis://localhost:6379 GET smoke_test_key)
echo "[smoke] Redis GET -> $VAL"

echo "[smoke] Postgres counts (feedback_events, token_usage)"
# run counts; if tables missing, errors are caught but script will continue because of || true
if docker exec -i sb_postgres psql -U soma -d somabrain -c "SELECT 'feedback_events' as tbl, count(*) FROM feedback_events;"; then
  :
else
  echo "[smoke] feedback_events missing or query failed"
fi
if docker exec -i sb_postgres psql -U soma -d somabrain -c "SELECT 'token_usage' as tbl, count(*) FROM token_usage;"; then
  :
else
  echo "[smoke] token_usage missing or query failed"
fi

echo "[smoke] DONE"
