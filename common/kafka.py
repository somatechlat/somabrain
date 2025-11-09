from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any, Dict, Optional

try:  # Optional runtime dependency; tests may not install kafka-python
    from kafka import KafkaProducer  # type: ignore
except Exception:  # pragma: no cover
    KafkaProducer = None  # type: ignore

try:  # Avro serde utilities (optional)
    from libs.kafka_cog.avro_schemas import load_schema  # type: ignore
    from libs.kafka_cog.serde import AvroSerde  # type: ignore
except Exception:  # pragma: no cover
    load_schema = None  # type: ignore
    AvroSerde = None  # type: ignore


def _bootstrap_url() -> str:
    url = os.getenv("SOMABRAIN_KAFKA_URL") or "localhost:30001"
    return url.replace("kafka://", "")


def make_producer() -> Optional[KafkaProducer]:  # pragma: no cover - integration path
    if KafkaProducer is None:
        return None
    return KafkaProducer(bootstrap_servers=_bootstrap_url(), acks="1", linger_ms=5)


@lru_cache(maxsize=32)
def get_serde(schema_name: str) -> Optional[AvroSerde]:
    if load_schema is None or AvroSerde is None:
        return None
    try:
        return AvroSerde(load_schema(schema_name))  # type: ignore[arg-type]
    except Exception:  # pragma: no cover
        return None


def encode(record: Dict[str, Any], schema_name: Optional[str]) -> bytes:
    serde = get_serde(schema_name) if schema_name else None
    if serde is not None:
        try:
            return serde.serialize(record)
        except Exception:  # pragma: no cover
            pass
    return json.dumps(record).encode("utf-8")


TOPICS = {
    "state": "cog.state.updates",
    "agent": "cog.agent.updates",
    "action": "cog.action.updates",
    "next": "cog.next.events",
    "soma_state": "soma.belief.state",
    "soma_agent": "soma.belief.agent",
    "soma_action": "soma.belief.action",
}
