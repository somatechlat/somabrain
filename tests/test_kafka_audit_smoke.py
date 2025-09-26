import json
import os
import time

import pytest
from kafka import KafkaConsumer, KafkaProducer


def _kafka_available(bootstrap):
    try:
        p = KafkaProducer(bootstrap_servers=bootstrap, request_timeout_ms=1000)
        p.close()
        return True
    except Exception:
        return False


@pytest.mark.integration
def test_kafka_audit_smoke_roundtrip():
    bootstrap = os.getenv("SOMA_KAFKA_URL", "127.0.0.1:9092")
    if not _kafka_available(bootstrap):
        pytest.skip("NO_MOCKS: Kafka not available at SOMA_KAFKA_URL")

    topic = os.getenv("SOMA_AUDIT_TOPIC", "soma.audit")
    # Try to create topic if missing (best-effort)
    try:
        import subprocess

        subprocess.run(
            [
                "python3",
                "scripts/create_audit_topic.py",
                "--bootstrap-server",
                bootstrap,
            ],
            check=False,
        )
    except Exception:
        pass

    producer = KafkaProducer(
        bootstrap_servers=bootstrap,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    ev = {
        "event_id": "smoke-1",
        "timestamp": int(time.time()),
        "request_id": "req-smoke",
        "user": "smoke",
        "input": {"q": "hi"},
        "decision": True,
        "violations": None,
        "constitution_sha": "sha-smoke",
        "constitution_sig": "sig-smoke",
    }
    try:
        producer.send(topic, ev)
        producer.flush(timeout=5)
    except Exception as exc:
        # If Kafka is not reachable, skip the test rather than error.
        pytest.skip(f"Kafka not reachable during send: {exc}")
    finally:
        producer.close()

    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=bootstrap,
        auto_offset_reset="earliest",
        consumer_timeout_ms=5000,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    )
    found = False
    for msg in consumer:
        v = msg.value
        if v.get("event_id") == "smoke-1":
            found = True
            assert v.get("constitution_sha") == "sha-smoke"
            assert v.get("constitution_sig") == "sig-smoke"
            break
    consumer.close()
    assert found, "Did not find smoke event in Kafka"
