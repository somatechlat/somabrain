"""
WM Updates Cache Worker
-----------------------

Consumes the three BeliefUpdate topics and pushes recent updates into Redis
lists per tenant/domain as a short-lived working-memory cache.

Keys: wm:updates:{tenant}:{domain}
 - Store last N (configurable) items
 - Set TTL per key (default 8s)

Feature gating is centralized via somabrain.modes.feature_enabled("wm_updates_cache"); legacy SOMABRAIN_FF_WM_UPDATES_CACHE removed.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from somabrain.modes import feature_enabled
from django.conf import settings

logger = logging.getLogger(__name__)

# Strict: use confluent-kafka Consumer only
from confluent_kafka import Consumer as CKConsumer
from somabrain.common.infra import assert_ready

try:  # Redis optional
    import redis
except Exception:  # pragma: no cover
    redis = None

try:
    from libs.kafka_cog.avro_schemas import load_schema
    from libs.kafka_cog.serde import AvroSerde
except Exception:  # pragma: no cover
    load_schema = None
    AvroSerde = None


def _bootstrap() -> str:
    """Execute bootstrap."""

    url = getattr(settings, "KAFKA_BOOTSTRAP_SERVERS", "")
    if not url:
        raise ValueError("SOMABRAIN_KAFKA_URL not set; refusing to fall back to localhost")
    return url.replace("kafka://", "")


def _redis_client():
    """Execute redis client."""

    url = getattr(settings, "SOMABRAIN_REDIS_URL", "") or ""
    if not url or redis is None:
        return None
    try:
        return redis.Redis.from_url(url)
    except Exception:
        return None


def _serde() -> Optional[AvroSerde]:
    """Execute serde."""

    if load_schema is None or AvroSerde is None:
        return None
    try:
        return AvroSerde(load_schema("belief_update"))  # type: ignore
    except Exception:
        return None


def _decode(payload: bytes, serde: Optional[AvroSerde]) -> Optional[Dict[str, Any]]:
    """Execute decode.

    Args:
        payload: The payload.
        serde: The serde.
    """

    if serde is not None:
        try:
            return json.loads(payload.decode("utf-8"))  # type: ignore
        except Exception:
            pass
    try:
        return serde.decode(payload)  # type: ignore
    except Exception:
        return None


def run_forever() -> None:  # pragma: no cover - integration loop
    """Execute run forever."""

    if not feature_enabled("wm_updates_cache"):
        print("wm_updates_cache: feature flag disabled; exiting.")
        return
    # Fail-fast infra readiness (Kafka + Redis required)
    assert_ready(
        require_kafka=True,
        require_redis=True,
        require_postgres=False,
        require_opa=False,
    )
    r = _redis_client()
    max_items = int(getattr(settings, "wm_updates_max_items", 50) or 50)
    ttl_seconds = int(getattr(settings, "wm_updates_ttl_seconds", 8) or 8)
    consumer = CKConsumer(
        {
            "bootstrap.servers": _bootstrap(),
            "group.id": getattr(settings, "consumer_group", "wm-updates-cache"),
            "enable.auto.commit": True,
            "auto.offset.reset": "latest",
        }
    )
    consumer.subscribe(
        [
            "cog.state.updates",
            "cog.agent.updates",
            "cog.action.updates",
        ]
    )
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
                except Exception as parse_exc:
                    logger.debug("Failed to parse tenant from event evidence: %s", parse_exc)
                domain = str(ev.get("domain") or "state").strip().lower()
                key = f"wm:updates:{tenant}:{domain}"
                if r is not None:
                    try:
                        # push JSON; trim to max_items; set TTL
                        r.lpush(key, json.dumps(ev))
                        if max_items > 0:
                            r.ltrim(key, 0, max_items - 1)
                        if ttl_seconds > 0:
                            r.expire(key, ttl_seconds)
                    except Exception as redis_exc:
                        logger.warning(
                            "Failed to cache WM update to Redis key %s: %s",
                            key,
                            redis_exc,
                        )
            except Exception as outer_exc:
                # Log and continue processing other messages
                logger.debug("Failed to process WM update message: %s", outer_exc)
    finally:
        try:
            consumer.close()
        except Exception as close_exc:
            logger.debug("Failed to close consumer: %s", close_exc)


def main() -> None:  # pragma: no cover
    """Execute main."""

    run_forever()


if __name__ == "__main__":  # pragma: no cover
    main()
