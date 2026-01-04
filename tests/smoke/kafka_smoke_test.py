#!/usr/bin/env python3
"""Simple Kafka smoke test: produce a unique message and consume it to verify broker readiness.

This script is intended for CI. It will produce one message to the configured topic and
attempt to consume it within a short timeout. Returns exit code 0 on success, non-zero on failure.
"""

import argparse
import json
import time
import uuid

from kafka import KafkaConsumer, KafkaProducer


def main():
    """Execute main."""

    p = argparse.ArgumentParser()
    p.add_argument("--bootstrap-server", default="127.0.0.1:9092")
    p.add_argument("--topic", default="soma.audit")
    p.add_argument("--timeout", type=int, default=10)
    args = p.parse_args()

    bs = args.bootstrap_server
    if bs.startswith("kafka://"):
        bs = bs[len("kafka://") :]

    key = str(uuid.uuid4())
    payload = {"smoke": True, "id": key, "ts": time.time()}

    try:
        producer = KafkaProducer(
            bootstrap_servers=bs,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            acks="all",
        )
        fut = producer.send(args.topic, payload)
        fut.get(timeout=5)
        producer.flush()
    except Exception as e:
        print(f"Producer failed: {e}")
        return 2

    # Try to consume the message
    try:
        consumer = KafkaConsumer(
            args.topic,
            bootstrap_servers=bs,
            auto_offset_reset="earliest",
            consumer_timeout_ms=args.timeout * 1000,
            enable_auto_commit=False,
            value_deserializer=lambda b: json.loads(b.decode("utf-8")),
        )
        start = time.time()
        for msg in consumer:
            try:
                v = msg.value
                if isinstance(v, dict) and v.get("id") == key:
                    print("Smoke test succeeded: message roundtrip confirmed")
                    return 0
            except Exception:
                continue
            if time.time() - start > args.timeout:
                break
        print("Smoke test failed: message not observed in topic within timeout")
        return 3
    except Exception as e:
        print(f"Consumer failed: {e}")
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
