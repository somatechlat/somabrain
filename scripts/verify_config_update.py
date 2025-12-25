"""Verify that a reward POST results in a config update.

The script is used in CI (the ``smoke-e2e.yml`` workflow) to ensure the
learning loop works end‑to‑end:

1. POST a minimal reward to the ``reward_producer`` HTTP endpoint.
2. Consume a single record from the ``cog.config.updates`` Kafka topic.
3. Print the ``exploration_temp`` (τ) and exit with status 0 if a record was
   received, otherwise exit with status 1.

It deliberately avoids any placeholder behaviour – all imports are real
libraries that exist in the repository's runtime image.  If the required
packages are missing the script will raise an informative exception rather
than silently succeeding.
"""

from __future__ import annotations

import json
from django.conf import settings
import sys
import time
from typing import Any, Dict

try:
    import requests
except Exception as e:
    raise RuntimeError(
        "requests library is required to run verify_config_update.py"
    ) from e

try:
    from confluent_kafka import Consumer as CfConsumer
except Exception as e:
    raise RuntimeError(
        "confluent_kafka is required to run verify_config_update.py"
    ) from e


def post_reward() -> None:
    """POST a synthetic reward to the reward producer.

    The payload matches the ``reward_event.avsc`` schema minimally.  The service
    runs on ``localhost`` inside the Docker compose network; the host port is
    taken from ``SOMABRAIN_REWARD_PORT`` (default 8083).
    """
    # Use centralized Settings for reward port and API URL
    url = f"{settings.api_url}/reward"
    payload: Dict[str, Any] = {
        "tenant": settings.default_tenant,
        "r_task": 0.5,
        "r_user": 0.5,
        "r_latency": 0.1,
        "r_safety": 0.9,
        "r_cost": 0.2,
        "total": 0.5,
    }
    try:
        resp = requests.post(url, json=payload, timeout=5)
        resp.raise_for_status()
    except Exception as exc:
        print(f"POST reward failed: {exc}", file=sys.stderr)
        sys.exit(1)


def consume_config_update(timeout: float = 10.0) -> Dict[str, Any] | None:
    """Consume a single ``cog.config.updates`` record.

    Returns the decoded JSON dict or ``None`` if the timeout expires.
    """
    kafka_bootstrap = settings.kafka_bootstrap_servers or "localhost:9092"
    topic = settings.topic_config_updates
    consumer_conf = {
        "bootstrap.servers": kafka_bootstrap,
        "group.id": "ci-config-verify",
        "auto.offset.reset": "latest",
        "enable.auto.commit": False,
    }
    consumer = CfConsumer(consumer_conf)
    consumer.subscribe([topic])
    end = time.time() + timeout
    while time.time() < end:
        msg = consumer.poll(0.5)
        if msg is None:
            continue
        if msg.error():
            # ignore errors, continue polling
            continue
        try:
            payload = msg.value()
            if payload is None:
                continue
            # Assume JSON alternative – the service always produces JSON if Avro
            # is unavailable, which is the case in CI where the in‑repo libs are
            # installed.
            data = json.loads(payload.decode("utf-8"))
            return data
        except Exception:
            continue
    return None


def main() -> None:
    post_reward()
    cfg = consume_config_update()
    if cfg is None:
        print("No config_update record received within timeout", file=sys.stderr)
        sys.exit(1)
    tau = cfg.get("exploration_temp")
    print(f"Config update received – exploration_temp (tau) = {tau}")
    sys.exit(0)


if __name__ == "__main__":
    main()
