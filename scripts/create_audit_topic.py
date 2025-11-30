#!/usr/bin/env python3
"""Create soma.audit topic using kafka-python. Intended for CI and local setup.
Usage: python scripts/create_audit_topic.py --bootstrap-server 127.0.0.1:9092 --partitions 6 --replication 1
"""
import argparse

from kafka import KafkaAdminClient, NewTopic


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--bootstrap-server", default="127.0.0.1:9092")
    p.add_argument("--topic", default="soma.audit")
    p.add_argument("--partitions", type=int, default=6)
    p.add_argument("--replication", type=int, default=1)
    args = p.parse_args()

    bs = args.bootstrap_server
    # accept kafka:// prefix
    if bs.startswith("kafka://"):
        bs = bs[len("kafka://") :]

    # retry loop with exponential backoff: Kafka may be starting in CI
    last_exc = None
    backoff = 0.5
    for attempt in range(1, 9):
        try:
            admin = KafkaAdminClient(bootstrap_servers=bs, request_timeout_ms=2000)
            break
        except Exception as e:
            last_exc = e
            print(
                f"Attempt {attempt}: Kafka bootstrap not ready at {bs}, retrying in {backoff}s...",
                flush=True,
            )
            import time

            time.sleep(backoff)
            backoff = min(backoff * 2, 5.0)
    else:
        print(f"Failed to connect to Kafka bootstrap {bs} after retries: {last_exc}")
        return
    topics = admin.list_topics()
    if args.topic in topics:
        print(f"Topic {args.topic} already exists")
        return
    topic = NewTopic(
        name=args.topic,
        num_partitions=args.partitions,
        replication_factor=args.replication,
    )
    try:
        admin.create_topics([topic], timeout_ms=10000)
        print(f"Created topic {args.topic}")
    except Exception as e:
        # idempotent create: if topic exists concurrently, the admin may raise
        print(f"Failed to create topic {args.topic}: {e}")


if __name__ == "__main__":
    main()
