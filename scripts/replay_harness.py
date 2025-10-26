#!/usr/bin/env python3
"""Replay Harness (synthetic)

Emits a small burst of BeliefUpdate events to the three update topics
to sanity-check the pipeline locally. Uses Avro if available, otherwise JSON.
"""
from __future__ import annotations

import json
import os
import random
import time
from typing import Any, Dict, Optional

try:
    from kafka import KafkaProducer  # type: ignore
except Exception:  # pragma: no cover
    KafkaProducer = None  # type: ignore

try:
    from libs.kafka_cog.avro_schemas import load_schema  # type: ignore
    from libs.kafka_cog.serde import AvroSerde  # type: ignore
except Exception:  # pragma: no cover
    load_schema = None  # type: ignore
    AvroSerde = None  # type: ignore


def _bootstrap() -> str:
    url = os.getenv("SOMABRAIN_KAFKA_URL") or "localhost:30001"
    return url.replace("kafka://", "")


def _serde() -> Optional[AvroSerde]:
    if load_schema is None or AvroSerde is None:
        return None
    try:
        return AvroSerde(load_schema("belief_update"))  # type: ignore[arg-type]
    except Exception:
        return None


def _enc(rec: Dict[str, Any], serde: Optional[AvroSerde]) -> bytes:
    if serde is not None:
        try:
            return serde.serialize(rec)
        except Exception:
            pass
    return json.dumps(rec).encode("utf-8")


def main() -> None:
    if KafkaProducer is None:
        print("Kafka client not installed; aborting.")
        return
    prod = KafkaProducer(bootstrap_servers=_bootstrap(), acks="1", linger_ms=5)
    serde = _serde()
    tenant = os.getenv("SOMABRAIN_DEFAULT_TENANT", "public")
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    try:
        for i in range(10):
            recs = [
                {
                    "topic": "cog.state.updates",
                    "record": {
                        "domain": "state",
                        "ts": now,
                        "delta_error": 0.2 + 0.05 * random.random(),
                        "confidence": 0.7 + 0.2 * random.random(),
                        "evidence": {"tenant": tenant, "src": "harness"},
                        "posterior": {},
                        "model_ver": "v1",
                        "latency_ms": 10,
                    },
                },
                {
                    "topic": "cog.agent.updates",
                    "record": {
                        "domain": "agent",
                        "ts": now,
                        "delta_error": 0.15 + 0.1 * random.random(),
                        "confidence": 0.6 + 0.3 * random.random(),
                        "evidence": {"tenant": tenant, "src": "harness"},
                        "posterior": {"intent": random.choice(["browse", "purchase"])},
                        "model_ver": "v1",
                        "latency_ms": 12,
                    },
                },
                {
                    "topic": "cog.action.updates",
                    "record": {
                        "domain": "action",
                        "ts": now,
                        "delta_error": 0.25 + 0.1 * random.random(),
                        "confidence": 0.5 + 0.4 * random.random(),
                        "evidence": {"tenant": tenant, "src": "harness"},
                        "posterior": {"next_action": random.choice(["search", "quote"])},
                        "model_ver": "v1",
                        "latency_ms": 14,
                    },
                },
            ]
            for r in recs:
                prod.send(r["topic"], value=_enc(r["record"], serde))
            time.sleep(0.2)
        prod.flush(2)
        print("Replay harness sent synthetic updates.")
    finally:
        try:
            prod.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
