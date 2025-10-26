from __future__ import annotations

import json
import os
import sys
import time
from typing import Any

try:
    import requests  # type: ignore
except Exception:
    # requests may not be installed in CI uv env; fallback to stdlib
    import urllib.request as _rq  # type: ignore

    class _Resp:
        def __init__(self, code: int, data: bytes):
            self.status_code = code
            self._data = data

        def json(self) -> Any:
            return json.loads(self._data.decode("utf-8"))

    def _post(url: str, json_body: Any) -> _Resp:
        req = _rq.Request(url, data=json.dumps(json_body).encode("utf-8"), headers={"Content-Type": "application/json"})
        with _rq.urlopen(req, timeout=10) as resp:  # type: ignore
            return _Resp(getattr(resp, "status", 200), resp.read())
else:
    def _post(url: str, json_body: Any):  # type: ignore
        return requests.post(url, json=json_body, timeout=10)


def _bootstrap() -> str:
    url = os.getenv("SOMABRAIN_KAFKA_URL") or "kafka://127.0.0.1:30001"
    return url.replace("kafka://", "")


def _consume_one(topic: str, timeout_s: float = 30.0) -> bool:
    try:
        from kafka import KafkaConsumer  # type: ignore
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


def main() -> int:
    # 0) Prepare a consumer at 'latest' BEFORE posting so we only capture new events
    try:
        from kafka import KafkaConsumer  # type: ignore
    except Exception:
        KafkaConsumer = None  # type: ignore
    consumer = None
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
    port = int(os.getenv("REWARD_PRODUCER_PORT", os.getenv("REWARD_PRODUCER_HOST_PORT", "30183")))
    url = f"http://127.0.0.1:{port}/reward/test-frame"
    payload = {"r_task": 0.9, "r_user": 0.8, "r_latency": 0.1, "r_safety": 0.95, "r_cost": 0.05}
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
        ok = _consume_one("cog.reward.events", timeout_s=45.0)
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
