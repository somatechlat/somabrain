#!/usr/bin/env python3
"""
Replay buffered audit events from Redis or durable journal to Kafka.
Safe, idempotent, and logs all actions. Usage:

    python scripts/replay_audit_buffer.py [--source redis|journal] [--limit N]

- By default, tries Redis buffer first, then journal fallback.
- Requires SOMABRAIN_KAFKA_URL and SOMA_AUDIT_TOPIC env vars.
"""
import os
import argparse
import json
import logging
from typing import Optional

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger("replay_audit_buffer")

try:
    import redis
except ImportError:
    redis = None
try:
    from kafka import KafkaProducer
except ImportError:
    KafkaProducer = None

AUDIT_JOURNAL_PATH = os.getenv("SOMA_AUDIT_JOURNAL_PATH", "./audit_log.jsonl")
REDIS_HOST = os.getenv("SOMABRAIN_REDIS_HOST", "localhost")
REDIS_PORT = os.getenv("SOMABRAIN_REDIS_PORT", "6379")
REDIS_URL = os.getenv("SOMABRAIN_REDIS_URL", f"redis://{REDIS_HOST}:{REDIS_PORT}/0")
KAFKA_HOST = os.getenv("SOMABRAIN_KAFKA_HOST", "localhost")
KAFKA_PORT = os.getenv("SOMABRAIN_KAFKA_PORT", "9092")
KAFKA_URL = os.getenv("SOMABRAIN_KAFKA_URL", f"{KAFKA_HOST}:{KAFKA_PORT}")
AUDIT_TOPIC = os.getenv("SOMA_AUDIT_TOPIC", "soma.audit")


def replay_from_redis(limit: Optional[int] = None):
    if not redis:
        LOGGER.error("redis-py not installed")
        return 0
    client = redis.from_url(REDIS_URL)
    key = os.getenv("SOMA_AUDIT_BUFFER_KEY", "soma:audit:buffer")
    events = client.lrange(key, 0, -1)
    if not events:
        LOGGER.info("No events in Redis buffer %s", key)
        return 0
    LOGGER.info("Found %d events in Redis buffer", len(events))
    count = 0
    for raw in events[:limit]:
        try:
            event = json.loads(raw)
        except Exception as exc:
            LOGGER.warning("Invalid JSON in buffer: %s", exc)
            continue
        if send_to_kafka(event):
            count += 1
    LOGGER.info("Replayed %d events from Redis buffer", count)
    return count


def replay_from_journal(limit: Optional[int] = None):
        return 0
                (removed)
            -- Removed: audit now requires real Kafka; no journal fallback.
            def _normalize_kafka_url(val: str) -> str:
            def replay_from_journal(limit: Optional[int] = None):
                raise SystemExit("replay_audit_buffer.py is deprecated; audit journaling removed.")
                    choices=["redis"],
                else:
                    raise SystemExit("Only 'redis' source supported; journal removed.")
        producer = KafkaProducer(
            bootstrap_servers=KAFKA_URL,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            linger_ms=10,
        )
        producer.send(AUDIT_TOPIC, event)
        producer.flush()
        LOGGER.info("Sent event to Kafka topic %s", AUDIT_TOPIC)
        return True
    except Exception as exc:
        LOGGER.error("Kafka send failed: %s", exc)
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Replay buffered audit events to Kafka."
    )
    parser.add_argument(
        "--source",
        choices=["redis", "journal"],
        default=None,
        help="Source buffer (default: redis, fallback journal)",
    )
    parser.add_argument("--limit", type=int, default=None, help="Max events to replay")
    args = parser.parse_args()

    total = 0
    if args.source == "redis" or args.source is None:
        total += replay_from_redis(args.limit)
        if total == 0 and args.source is None:
            total += replay_from_journal(args.limit)
    elif args.source == "journal":
        total += replay_from_journal(args.limit)
    LOGGER.info("Total events replayed: %d", total)


if __name__ == "__main__":
    main()
