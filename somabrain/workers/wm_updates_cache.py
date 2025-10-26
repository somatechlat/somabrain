"""
WM Updates Cache Worker
-----------------------

Consumes the three BeliefUpdate topics and pushes recent updates into Redis
lists per tenant/domain as a short-lived working-memory cache.

Keys: wm:updates:{tenant}:{domain}
 - Store last N (configurable) items
 - Set TTL per key (default 8s)

Feature flag: SOMABRAIN_FF_WM_UPDATES_CACHE=1
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional

try:  # Kafka optional
    from kafka import KafkaConsumer  # type: ignore
except Exception:  # pragma: no cover
    KafkaConsumer = None  # type: ignore

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
    if os.getenv("SOMABRAIN_FF_WM_UPDATES_CACHE", "0").strip().lower() not in ("1", "true", "yes", "on"):
        print("wm_updates_cache: feature flag disabled; exiting.")
        return
    if KafkaConsumer is None:
        print("wm_updates_cache: Kafka client not available; exiting.")
        return
    r = _redis_client()
    if r is None:
        print("wm_updates_cache: Redis not available; exiting.")
        return
    max_items = int(os.getenv("WM_UPDATES_MAX_ITEMS", "50") or 50)
    ttl_seconds = int(os.getenv("WM_UPDATES_TTL_SECONDS", "8") or 8)
    consumer = KafkaConsumer(
        "cog.state.updates",
        "cog.agent.updates",
        "cog.action.updates",
        bootstrap_servers=_bootstrap(),
        value_deserializer=lambda m: m,
        auto_offset_reset="latest",
        enable_auto_commit=True,
        group_id=os.getenv("SOMABRAIN_CONSUMER_GROUP", "wm-updates-cache"),
    )
    serde = _serde()
    try:
        for msg in consumer:
            try:
                ev = _decode(msg.value, serde)
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
