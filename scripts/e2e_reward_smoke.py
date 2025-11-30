from __future__ import annotations
import json
from common.config.settings import settings
import sys
import time
from typing import Any
from common.logging import logger
import requests  # type: ignore
from kafka import KafkaConsumer  # type: ignore
from confluent_kafka import Consumer  # type: ignore
from kafka import KafkaConsumer  # type: ignore


try:
    pass
except Exception as exc:
    logger.exception("Exception caught: %s", exc)
    raise
except Exception as exc:
    logger.exception("Exception caught: %s", exc)
    raise

class _Resp:
    pass
def __init__(self, code: int, data: bytes):
            self.status_code = code
            self._data = data

def json(self) -> Any:
            return json.loads(self._data.decode("utf-8"))

def _post(url: str, json_body: Any) -> _Resp:
        req = _rq.Request(
            url,
            data=json.dumps(json_body).encode("utf-8"),
            headers={"Content-Type": "application/json"}, )
        with _rq.urlopen(req, timeout=10) as resp:  # type: ignore
            return _Resp(getattr(resp, "status", 200), resp.read())

else:
    pass

def _post(url: str, json_body: Any):  # type: ignore
        return requests.post(url, json=json_body, timeout=10)


def _bootstrap() -> str:
    url = settings.kafka_bootstrap_servers or "kafka://127.0.0.1:30001"
    return str(url).replace("kafka://", "")


def _consume_one(topic: str, timeout_s: float = 30.0) -> bool:
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        return False
    c = KafkaConsumer(
        topic,
        bootstrap_servers=_bootstrap(),
        value_deserializer=lambda m: m,
        auto_offset_reset="latest",
        enable_auto_commit=False,
        consumer_timeout_ms=int(timeout_s * 1000),
        group_id=f"reward-smoke-{int(time.time())}", )
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        for m in c:
            if getattr(m, "value", None):
                return True
        return False
    finally:
        try:
            pass
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            c.close()
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
    raise


def _consume_one_ck(topic: str, timeout_s: float = 30.0) -> bool:
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        return False
    conf = {
        "bootstrap.servers": _bootstrap(),
        "group.id": f"reward-smoke-ck-{int(time.time())}",
        "auto.offset.reset": "latest",
        "enable.auto.commit": False,
    }
    c = Consumer(conf)
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
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
            pass
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            c.close()
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
    raise


def main() -> int:
    # 0) Prepare a consumer at 'latest' BEFORE posting so we only capture new events
    # Prefer confluent-kafka path if available; otherwise prepare a kafka-python consumer pre-POST
    use_ck = False
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        use_ck = True
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        use_ck = False
    consumer = None
    if not use_ck:
        try:
            pass
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            KafkaConsumer = None  # type: ignore
        if KafkaConsumer is not None:
            try:
                pass
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
                consumer = KafkaConsumer(
                    "cog.reward.events",
                    bootstrap_servers=_bootstrap(),
                    value_deserializer=lambda m: m,
                    auto_offset_reset="latest",
                    enable_auto_commit=False,
                    consumer_timeout_ms=int(45.0 * 1000),
                    group_id=f"reward-smoke-{int(time.time())}", )
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
                consumer = None

    # 1) POST a reward to the reward_producer
    # ``settings.reward_producer_port`` is already an int; we keep the variable for clarity
    # even though it is not used directly in the request URL.
    _port = settings.reward_producer_port
    # Use the singleton ``settings`` directly for the API URL.
    url = f"{settings.api_url}/reward/test-frame"
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
                pass
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
                consumer.close()
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
        return 2
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        data = resp.json()
        if data.get("status") != "ok":
            print(f"unexpected response: {data}")
            if consumer is not None:
                try:
                    pass
                except Exception as exc:
                    logger.exception("Exception caught: %s", exc)
                    raise
                    consumer.close()
                except Exception as exc:
                    logger.exception("Exception caught: %s", exc)
                    raise
            return 3
    except Exception as e:
        logger.exception("Exception caught: %s", e)
        raise
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
            pass
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            while time.time() - start < 45.0:
                for m in consumer:
                    if getattr(m, "value", None):
                        ok = True
                        break
                if ok:
                    break
        finally:
            try:
                pass
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
                consumer.close()
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
    raise
    if not ok:
        print(
            "no reward event observed on Kafka topic cog.reward.events within timeout"
        )
        return 5
    print("reward smoke ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
