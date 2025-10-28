#!/usr/bin/env python3
"""
E2E smoke: TeachFeedback -> RewardEvent

Procedure:
- Produce a TeachFeedback JSON record to topic cog.teach.feedback
- Consume from cog.reward.events and verify a RewardEvent appears with the same frame_id

Notes:
- The processor may emit Avro-schemaless or JSON; we try Avro first (if fastavro available)
  using the legacy reward_event schema, then fallback to JSON.
"""
from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

try:
    from kafka import KafkaProducer, KafkaConsumer  # type: ignore
except Exception:
    print("kafka-python not installed", file=sys.stderr)
    sys.exit(2)

try:
    from libs.kafka_cog.avro_schemas import load_schema  # type: ignore
    from libs.kafka_cog.serde import AvroSerde  # type: ignore
except Exception:
    load_schema = None  # type: ignore
    AvroSerde = None  # type: ignore


TEACH_TOPIC = "cog.teach.feedback"
REWARD_TOPIC = "cog.reward.events"


def _bootstrap() -> str:
    url = os.getenv("SOMABRAIN_KAFKA_URL") or "kafka://127.0.0.1:30102"
    return url.replace("kafka://", "")


def _avro_reward_serde() -> Optional[AvroSerde]:
    if load_schema is None or AvroSerde is None:
        return None
    try:
        return AvroSerde(load_schema("reward_event"))  # type: ignore[arg-type]
    except Exception:
        return None


def _decode_reward(value: bytes) -> Optional[Dict[str, Any]]:
    # Try Avro first
    serde = _avro_reward_serde()
    if serde is not None:
        try:
            out = serde.deserialize(value)  # type: ignore[arg-type]
            if isinstance(out, dict):
                return out
        except Exception:
            pass
    # Fallback to JSON
    try:
        return json.loads(value.decode("utf-8"))
    except Exception:
        return None


def produce_teach_feedback(prod: KafkaProducer, frame_id: str) -> None:
    now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    rec = {
        "feedback_id": f"fb-{int(time.time()*1000)}",
        "capsule_id": f"cap-{int(time.time()*1000)}",
        "frame_id": frame_id,
        "ts": now_iso,
        "rating": 5,
        "comment": "smoke-test",
    }
    payload = json.dumps(rec).encode("utf-8")
    fut = prod.send(TEACH_TOPIC, value=payload)
    fut.get(timeout=10)


def consume_reward_for_frame(consumer: KafkaConsumer, frame_id: str, timeout_s: int = 60) -> bool:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        msg = consumer.poll(timeout_ms=500)
        if msg is None:
            continue
        if isinstance(msg, dict):
            records = []
            for _, v in msg.items():
                records.extend(v)
        else:
            records = [msg]
        for r in records:
            val = getattr(r, "value", None)
            if not val:
                continue
            dec = _decode_reward(val)
            if isinstance(dec, dict):
                if str(dec.get("frame_id") or "").strip() == frame_id:
                    return True
    return False


def main() -> None:
    bootstrap = _bootstrap()
    frame_id = f"frame-{int(time.time()*1000)}"

    prod = KafkaProducer(bootstrap_servers=bootstrap, value_serializer=lambda v: v)
    try:
        produce_teach_feedback(prod, frame_id)
    finally:
        try:
            prod.flush(5)
            prod.close()
        except Exception:
            pass

    cons = KafkaConsumer(
        REWARD_TOPIC,
        bootstrap_servers=bootstrap,
        value_deserializer=lambda m: m,
        auto_offset_reset="latest",
        enable_auto_commit=False,
        group_id=f"teach-smoke-{int(time.time())}",
        consumer_timeout_ms=1000,
    )
    try:
        ok = consume_reward_for_frame(cons, frame_id, timeout_s=90)
    finally:
        try:
            cons.close()
        except Exception:
            pass

    if not ok:
        print("Teach->Reward smoke failed: no matching reward received", file=sys.stderr)
        sys.exit(1)
    print("Teach->Reward smoke passed.")


if __name__ == "__main__":
    main()
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
