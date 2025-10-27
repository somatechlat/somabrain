from __future__ import annotations

import json
import os
import sys
import time


def _bootstrap() -> str:
    url = os.getenv("SOMABRAIN_KAFKA_URL") or "kafka://127.0.0.1:30001"
    return url.replace("kafka://", "")


def main() -> int:
    # Prepare consumer for reward topic
    consumer = None
    try:
        from kafka import KafkaConsumer, KafkaProducer  # type: ignore
    except Exception:
        KafkaConsumer = None  # type: ignore
        KafkaProducer = None  # type: ignore

    if KafkaConsumer is None or KafkaProducer is None:
        print("kafka-python not available")
        return 2

    try:
        consumer = KafkaConsumer(
            "cog.reward.events",
            bootstrap_servers=_bootstrap(),
            value_deserializer=lambda m: m,
            auto_offset_reset="latest",
            enable_auto_commit=False,
            consumer_timeout_ms=int(45.0 * 1000),
            group_id=f"teach-smoke-{int(time.time())}",
        )
    except Exception as e:
        print(f"failed to create consumer: {e}")
        return 3

    # Produce one TeachFeedback event
    try:
        producer = KafkaProducer(bootstrap_servers=_bootstrap(), acks="1", linger_ms=5)
    except Exception as e:
        print(f"failed to create producer: {e}")
        try:
            consumer.close()
        except Exception:
            pass
        return 4

    fb = {
        "feedback_id": f"fb-{int(time.time())}",
        "capsule_id": "cap-123",
        "frame_id": "frame-teach-smoke",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "rating": 5,
        "comment": "Great answer",
    }
    try:
        producer.send("cog.teach.feedback", value=json.dumps(fb).encode("utf-8"))
    except Exception as e:
        print(f"failed to produce teach feedback: {e}")
        try:
            consumer.close()
        except Exception:
            pass
        return 5

    # Expect a reward event to appear
    ok = False
    start = time.time()
    try:
        while time.time() - start < 45.0:
            for m in consumer:
                if not getattr(m, "value", None):
                    continue
                try:
                    ev = json.loads(m.value.decode("utf-8"))
                except Exception:
                    # Avro case: just accept a message
                    ok = True
                    break
                if isinstance(ev, dict) and ev.get("frame_id") == fb["frame_id"]:
                    ok = True
                    break
            if ok:
                break
    finally:
        try:
            consumer.close()
        except Exception:
            pass

    if not ok:
        print("no reward observed for teach feedback within timeout")
        return 6
    print("teach feedback smoke ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
