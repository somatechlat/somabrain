#!/usr/bin/env python3
from __future__ import annotations

from common.config.settings import settings
import sys
import time
from typing import Optional

try:
    from kafka import KafkaConsumer  # type: ignore
except Exception:
    print("ERROR: kafka-python not installed", file=sys.stderr)
    sys.exit(2)


def _bootstrap() -> str:
    url = settings.kafka_bootstrap_servers or "kafka://127.0.0.1:30001"
    return str(url).replace("kafka://", "").replace("PLAINTEXT://", "")


def _consume_one(topic: str, timeout_s: float = 30.0) -> Optional[bytes]:
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=_bootstrap(),
        value_deserializer=lambda m: m,
        auto_offset_reset="latest",
        enable_auto_commit=False,
        consumer_timeout_ms=int(max(1.0, timeout_s) * 1000),
        group_id=f"e2e-smoke-{int(time.time())}",
    )
    try:
        for msg in consumer:
            if getattr(msg, "value", None):
                return msg.value
        return None
    finally:
        try:
            consumer.close()
        except Exception:
            pass


def main() -> int:
    topics = [
        "cog.global.frame",
        "cog.segments",
    ]
    ok = True
    for t in topics:
        val = _consume_one(t, timeout_s=60)
        if val is None:
            print(
                f"E2E SMOKE: no message observed on topic '{t}' within timeout",
                file=sys.stderr,
            )
            ok = False
        else:
            print(f"E2E SMOKE: observed message on '{t}': {val[:128]!r}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
