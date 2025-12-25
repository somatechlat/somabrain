from __future__ import annotations

from django.conf import settings
import sys
import time


def _bootstrap() -> str:
    url = settings.kafka_bootstrap_servers or "kafka://127.0.0.1:30001"
    return str(url).replace("kafka://", "")


def main() -> int:
    try:
        from kafka import KafkaConsumer
    except Exception as e:
        print(f"kafka-python not available: {e}")
        return 2
    c = KafkaConsumer(
        "cog.next.events",
        bootstrap_servers=_bootstrap(),
        value_deserializer=lambda m: m,
        auto_offset_reset="latest",
        enable_auto_commit=False,
        consumer_timeout_ms=60000,
        group_id=f"next-smoke-{int(time.time())}",
    )
    try:
        for m in c:
            if getattr(m, "value", None):
                print("next-event smoke ok")
                return 0
        print("no next-event observed within timeout")
        return 1
    finally:
        try:
            c.close()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
