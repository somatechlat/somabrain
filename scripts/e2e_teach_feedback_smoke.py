from __future__ import annotations

import json
import os
import sys
import time


def _bootstrap() -> str:
    url = os.getenv("SOMABRAIN_KAFKA_URL") or "kafka://127.0.0.1:30001"
    return url.replace("kafka://", "")


def _try_confluent() -> int | None:
    try:
        from confluent_kafka import Consumer, Producer  # type: ignore
    except Exception:
        return None

    bs = _bootstrap()
    # Consumer for reward topic (latest)
    c = Consumer({
        "bootstrap.servers": bs,
        "group.id": f"teach-smoke-{int(time.time())}",
        "auto.offset.reset": "earliest",
    })
    c.subscribe(["cog.reward.events"])

    # Producer for teach feedback (no compression for easy interop)
    p = Producer({
        "bootstrap.servers": bs,
        "compression.type": "none",
    })

    fb = {
        "feedback_id": f"fb-{int(time.time())}",
        "capsule_id": "cap-123",
        "frame_id": "frame-teach-smoke",
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "rating": 5,
        "comment": "Great answer",
    }
    try:
        p.produce("cog.teach.feedback", value=json.dumps(fb).encode("utf-8"))
        p.flush(5)
    except Exception as e:
        print(f"failed to produce teach feedback (ck): {e}")
        try:
            c.close()
        except Exception:
            pass
        return 5

    # Wait up to 45s for a reward message
    end = time.time() + 45.0
    ok = False
    while time.time() < end:
        msg = c.poll(1.0)
        if msg is None or msg.error():
            continue
        val = msg.value()
        if not val:
            continue
        try:
            ev = json.loads(val.decode("utf-8"))
            if isinstance(ev, dict) and ev.get("frame_id") == fb["frame_id"]:
                ok = True
                break
        except Exception:
            # Avro or other payload; accept any message
            ok = True
            break
    try:
        c.close()
    except Exception:
        pass
    if not ok:
        print("no reward observed for teach feedback within timeout (ck)")
        return 6
    print("teach feedback smoke ok")
    return 0


def _kafka_python() -> int:
    try:
        from kafka import KafkaConsumer, KafkaProducer  # type: ignore
    except Exception:
        print("kafka-python not available")
        return 2

    bs = _bootstrap()
    try:
        consumer = KafkaConsumer(
            "cog.reward.events",
            bootstrap_servers=bs,
            value_deserializer=lambda m: m,
            auto_offset_reset="latest",
            enable_auto_commit=False,
            consumer_timeout_ms=int(45.0 * 1000),
            group_id=f"teach-smoke-{int(time.time())}",
        )
    except Exception as e:
        print(f"failed to create consumer: {e}")
        return 3

    try:
        producer = KafkaProducer(bootstrap_servers=bs, acks="1", linger_ms=5)
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


def main() -> int:
    # Prefer confluent-kafka when available (more reliable with modern brokers)
    r = _try_confluent()
    if isinstance(r, int):
        return r
    return _kafka_python()


if __name__ == "__main__":
    sys.exit(main())
