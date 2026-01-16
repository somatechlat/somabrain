"""Module e2e_reward_smoke."""

from __future__ import annotations

import json
from django.conf import settings
import sys
import time
from typing import Any

try:
    import requests
except Exception:
    # requests may not be installed in CI uv env; use stdlib alternative
    import urllib.request as _rq

    class _Resp:
        """Resp class implementation."""

        def __init__(self, code: int, data: bytes):
            """Initialize the instance."""

            self.status_code = code
            self._data = data

        def json(self) -> Any:
            """Execute json."""

            return json.loads(self._data.decode("utf-8"))

    def _post(url: str, json_body: Any) -> _Resp:
        """Execute post.

        Args:
            url: The url.
            json_body: The json_body.
        """

        req = _rq.Request(
            url,
            data=json.dumps(json_body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with _rq.urlopen(req, timeout=10) as resp:
            return _Resp(getattr(resp, "status", 200), resp.read())

else:

    def _post(url: str, json_body: Any):
        """Execute post.

        Args:
            url: The url.
            json_body: The json_body.
        """

        return requests.post(url, json=json_body, timeout=10)


def _bootstrap() -> str:
    """Execute bootstrap."""

    url = getattr(settings, "SOMABRAIN_KAFKA_BOOTSTRAP_SERVERS", "kafka://127.0.0.1:30001")
    return str(url).replace("kafka://", "")


def _consume_one(topic: str, timeout_s: float = 30.0) -> bool:
    """Execute consume one.

    Args:
        topic: The topic.
        timeout_s: The timeout_s.
    """

    try:
        from kafka import KafkaConsumer
    except Exception:
        return False
    c = KafkaConsumer(
        topic,
        bootstrap_servers=_bootstrap(),
        value_deserializer=lambda m: m,
        auto_offset_reset="latest",
        enable_auto_commit=False,
        consumer_timeout_ms=int(timeout_s * 1000),
        group_id=f"reward-smoke-{int(time.time())}",
    )
    try:
        for m in c:
            if getattr(m, "value", None):
                return True
        return False
    finally:
        try:
            c.close()
        except Exception:
            pass


def _consume_one_ck(topic: str, timeout_s: float = 30.0) -> bool:
    """Execute consume one ck.

    Args:
        topic: The topic.
        timeout_s: The timeout_s.
    """

    try:
        from confluent_kafka import Consumer
    except Exception:
        return False
    conf = {
        "bootstrap.servers": _bootstrap(),
        "group.id": f"reward-smoke-ck-{int(time.time())}",
        "auto.offset.reset": "latest",
        "enable.auto.commit": False,
    }
    c = Consumer(conf)
    try:
        c.subscribe([topic])
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            msg = c.poll(0.5)
            if msg is None:
                continue
            if msg.error():
                continue
            if msg.value():
                return True
        return False
    finally:
        try:
            c.close()
        except Exception:
            pass


def main() -> int:
    # 0) Prepare a consumer at 'latest' BEFORE posting so we only capture new events
    # Prefer confluent-kafka path if available; otherwise prepare a kafka-python consumer pre-POST
    """Execute main."""

    use_ck = False
    try:
        use_ck = True
    except Exception:
        use_ck = False
    consumer = None
    if not use_ck:
        try:
            from kafka import KafkaConsumer
        except Exception:
            KafkaConsumer = None
        if KafkaConsumer is not None:
            try:
                consumer = KafkaConsumer(
                    "cog.reward.events",
                    bootstrap_servers=_bootstrap(),
                    value_deserializer=lambda m: m,
                    auto_offset_reset="latest",
                    enable_auto_commit=False,
                    consumer_timeout_ms=int(45.0 * 1000),
                    group_id=f"reward-smoke-{int(time.time())}",
                )
            except Exception:
                consumer = None

    # 1) POST a reward to the reward_producer
    # ``SOMABRAIN_REWARD_PRODUCER_PORT`` is available from settings; we keep the variable for clarity
    # even though it is not used directly in the request URL.
    _port = getattr(settings, "SOMABRAIN_REWARD_PRODUCER_PORT", 30183)
    # Use the singleton ``settings`` directly for the API URL.
    url = f"{getattr(settings, 'SOMABRAIN_API_URL', 'http://localhost:30101')}/reward/test-frame"
    payload = {
        "r_task": 0.9,
        "r_user": 0.8,
        "r_latency": 0.1,
        "r_safety": 0.95,
        "r_cost": 0.05,
    }
    resp = _post(url, payload)
    code = getattr(resp, "status_code", 200)
    if code >= 300:
        print(f"reward POST failed: {code}")
        if consumer is not None:
            try:
                consumer.close()
            except Exception:
                pass
        return 2
    try:
        data = resp.json()
        if data.get("status") != "ok":
            print(f"unexpected response: {data}")
            if consumer is not None:
                try:
                    consumer.close()
                except Exception:
                    pass
            return 3
    except Exception as e:
        print(f"invalid response: {e}")
        if consumer is not None:
            try:
                consumer.close()
            except Exception:
                pass
        return 4

    # 2) Consume one record from cog.reward.events
    if consumer is None:
        # Prefer confluent-kafka consumer if available
        ok = _consume_one_ck("cog.reward.events", timeout_s=45.0) or _consume_one(
            "cog.reward.events", timeout_s=45.0
        )
    else:
        ok = False
        start = time.time()
        try:
            while time.time() - start < 45.0:
                for m in consumer:
                    if getattr(m, "value", None):
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
        print("no reward event observed on Kafka topic cog.reward.events within timeout")
        return 5
    print("reward smoke ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
