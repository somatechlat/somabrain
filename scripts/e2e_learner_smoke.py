from __future__ import annotations

import json
from common.config.settings import settings as shared_settings
import sys
import time
from typing import Any

try:
    import requests  # type: ignore
except Exception:
    import urllib.request as _rq  # type: ignore

    class _Resp:
        def __init__(self, code: int, data: bytes) -> None:
            self.status_code = code
            self._data = data

        def json(self) -> Any:
            return json.loads(self._data.decode("utf-8"))

    def _post(url: str, body: Any) -> _Resp:
        req = _rq.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with _rq.urlopen(req, timeout=10) as resp:  # type: ignore
            return _Resp(getattr(resp, "status", 200), resp.read())

else:

    def _post(url: str, body: Any):  # type: ignore
        return requests.post(url, json=body, timeout=10)


def _bootstrap() -> str:
    url = shared_settings.kafka_bootstrap_servers or "kafka://127.0.0.1:30001"
    return str(url).replace("kafka://", "")


def _consume_one(topic: str, timeout_s: float) -> bool:
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
        group_id=f"learner-smoke-{int(time.time())}",
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
    # Ensure reward -> config_update loop works end-to-end
    # 1) POST a reward to reward_producer
    rport = int(
        os.getenv(
            "REWARD_PRODUCER_PORT", os.getenv("REWARD_PRODUCER_HOST_PORT", "30183")
        )
    )
    from common.config.settings import settings as _settings
    url = f"{_settings.api_url}/reward/test-frame-learner"
    payload = {
        "r_task": 0.85,
        "r_user": 0.9,
        "r_latency": 0.1,
        "r_safety": 0.95,
        "r_cost": 0.05,
    }
    resp = _post(url, payload)
    code = getattr(resp, "status_code", 200)
    if code >= 300:
        print(f"reward POST failed: {code}")
        return 2
    try:
        ok = resp.json().get("status") == "ok"
    except Exception:
        ok = False
    if not ok:
        print("reward producer response invalid")
        return 3

    # 2) Observe a config update from learner_online
    ok2 = _consume_one("cog.config.updates", timeout_s=60.0)
    if not ok2:
        print("no config update observed within timeout")
        return 4
    print("learner loop smoke ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
