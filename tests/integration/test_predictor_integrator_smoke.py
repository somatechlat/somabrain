import os
import json
import time
import socket
import uuid

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _require_backends(monkeypatch):
    # Force readiness checks in this integration test
    monkeypatch.setenv("SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS", "1")


def _kafka_bootstrap():
    return os.getenv("SOMABRAIN_KAFKA_URL") or os.getenv("KAFKA_BOOTSTRAP_SERVERS") or "localhost:9092"


@pytest.fixture
def _topics():
    return {
        "state": "cog.state.updates",
        "agent": "cog.agent.updates",
        "action": "cog.action.updates",
        "global": "cog.global.frame",
    }


def _producer():
    from confluent_kafka import Producer

    return Producer({"bootstrap.servers": _kafka_bootstrap()})


def _consumer(topic):
    from confluent_kafka import Consumer

    c = Consumer(
        {
            "bootstrap.servers": _kafka_bootstrap(),
            "group.id": f"smoke-{uuid.uuid4().hex}",
            "auto.offset.reset": "earliest",
        }
    )
    c.subscribe([topic])
    return c


@pytest.fixture
def integrator(_topics):
    from somabrain.services.integrator_hub_triplet import IntegratorHub

    hub = IntegratorHub(
        start_io=True,
        start_health=False,
        topic_updates=_topics,
        topic_global=_topics["global"],
    )
    yield hub
    try:
        if hub.consumer:
            hub.consumer.close()
    except Exception:
        pass


def _send_update(domain, producer, topics, confidence=0.8, delta_error=0.2):
    rec = {
        "domain": domain,
        "confidence": confidence,
        "delta_error": delta_error,
        "ts": time.time(),
    }
    producer.produce(topics[domain], json.dumps(rec).encode("utf-8"))
    producer.flush()


@pytest.mark.timeout(10)
def test_predictor_to_integrator_smoke(integrator, _topics):
    prod = _producer()
    cons = _consumer(_topics["global"])
    for d in ["state", "agent", "action"]:
        _send_update(d, prod, _topics, confidence=0.5, delta_error=0.1 if d == "state" else 0.9)
    deadline = time.time() + 8
    leader = None
    while time.time() < deadline:
        msg = cons.poll(1.0)
        if msg is None:
            continue
        if msg.error():
            continue
        try:
            payload = json.loads(msg.value())
            leader = payload.get("leader")
            if leader:
                break
        except Exception:
            continue
    assert leader == "state"

