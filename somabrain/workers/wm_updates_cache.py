"""
WM Updates Cache Worker
-----------------------

Consumes the three BeliefUpdate topics and pushes recent updates into Redis
lists per tenant/domain as a short-lived working-memory cache.

Keys: wm:updates:{tenant}:{domain}
 - Store last N (configurable) items
 - Set TTL per key (default 8s)

Enablement: governed by SOMABRAIN_MODE via mode_config (ties to integrator enablement)
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

# Strict: use confluent-kafka Consumer only
from confluent_kafka import Consumer as CKConsumer  # type: ignore
from somabrain.common.infra import assert_ready

try:  # Redis optional
    import redis  # type: ignore
except Exception:  # pragma: no cover
    redis = None  # type: ignore

try:
    from libs.kafka_cog.avro_schemas import load_schema  # type: ignore
    from libs.kafka_cog.serde import AvroSerde  # type: ignore
except Exception:  # pragma: no cover
    load_schema = None  # type: ignore
    AvroSerde = None  # type: ignore


def _bootstrap() -> str:
    url = os.getenv("SOMABRAIN_KAFKA_URL") or "localhost:30001"
    return url.replace("kafka://", "")


def _redis_client():
    url = os.getenv("SOMABRAIN_REDIS_URL") or ""
    if not url or redis is None:
        return None
    try:
        return redis.Redis.from_url(url)
    except Exception:
        return None


def _serde() -> Optional[AvroSerde]:
    if load_schema is None or AvroSerde is None:
        return None
    try:
        return AvroSerde(load_schema("belief_update"))  # type: ignore[arg-type]
    except Exception:
        return None


def _decode(payload: bytes, serde: Optional[AvroSerde]) -> Optional[Dict[str, Any]]:
    if serde is not None:
        try:
            return serde.deserialize(payload)
        except Exception:
            pass
    try:
        return json.loads(payload.decode("utf-8"))
    except Exception:
        return None


def run_forever() -> None:  # pragma: no cover - integration loop
    try:
        from somabrain.modes import mode_config
        if not mode_config().enable_integrator:
            print("wm_updates_cache: disabled via mode; exiting.")
            return
    except Exception:
        return
    # Fail-fast infra readiness (Kafka + Redis required)
    assert_ready(require_kafka=True, require_redis=True, require_postgres=False, require_opa=False)
    r = _redis_client()
    max_items = int(os.getenv("WM_UPDATES_MAX_ITEMS", "50") or 50)
    ttl_seconds = int(os.getenv("WM_UPDATES_TTL_SECONDS", "8") or 8)
    consumer = CKConsumer({
        "bootstrap.servers": _bootstrap(),
        "group.id": os.getenv("SOMABRAIN_CONSUMER_GROUP", "wm-updates-cache"),
        "enable.auto.commit": True,
        "auto.offset.reset": "latest",
    })
    consumer.subscribe([
        "cog.state.updates",
        "cog.agent.updates",
        "cog.action.updates",
    ])
    serde = _serde()
    try:
        while True:
            msg = consumer.poll(timeout=1.0)
            if msg is None or msg.error():
                continue
            try:
                ev = _decode(msg.value(), serde)
                if not isinstance(ev, dict):
                    continue
                tenant = "public"
                try:
                    evd = ev.get("evidence") or {}
                    tenant = str(evd.get("tenant") or "public").strip() or "public"
                except Exception:
                    pass
                domain = str(ev.get("domain") or "state").strip().lower()
                key = f"wm:updates:{tenant}:{domain}"
                try:
                    # push JSON; trim to max_items; set TTL
                    r.lpush(key, json.dumps(ev))
                    if max_items > 0:
                        r.ltrim(key, 0, max_items - 1)
                    if ttl_seconds > 0:
                        r.expire(key, ttl_seconds)
                except Exception:
                    pass
            except Exception:
                # swallow and continue
                pass
    finally:
        try:
            consumer.close()
        except Exception:
            pass


def main() -> None:  # pragma: no cover
    run_forever()


if __name__ == "__main__":  # pragma: no cover
    main()
