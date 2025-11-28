from __future__ import annotations

import json
from common.config.settings import settings
from functools import lru_cache
from typing import Any, Dict, Optional

try:  # Strict mode: use confluent-kafka only
    from confluent_kafka import Producer as CKProducer  # type: ignore
except Exception as e:  # pragma: no cover
    raise RuntimeError(f"common.kafka: confluent-kafka required: {e}")

try:  # Avro serde utilities (optional)
    from libs.kafka_cog.avro_schemas import load_schema  # type: ignore
    from libs.kafka_cog.serde import AvroSerde  # type: ignore
except Exception:  # pragma: no cover
    load_schema = None  # type: ignore
    AvroSerde = None  # type: ignore


def _bootstrap_url() -> str:
    """Get bootstrap servers from central Settings.

    Returns the ``kafka_bootstrap_servers`` field from the global ``settings``
    instance, ensuring any legacy environment variables are honoured via the
    Settings model's default handling. The value is stripped of a ``kafka://``
    scheme if present.
    """
    bs = settings.kafka_bootstrap_servers
    if not bs:
        raise RuntimeError(
            "Kafka bootstrap servers are required (settings.kafka_bootstrap_servers)"
        )
    return bs.replace("kafka://", "")


class _ProducerShim:
    """Shim to emulate kafka-python Producer.send API on top of confluent-kafka."""

    def __init__(self, ck: CKProducer) -> None:
        self._ck = ck

    def send(self, topic: str, value: bytes):  # mimic kafka-python
        if isinstance(value, (bytes, bytearray)):
            payload = value
        else:
            # Allow dict payloads for non-Avro topics (temporary until schemas exist)
            payload = json.dumps(value).encode("utf-8")
        self._ck.produce(topic, value=payload)

        # return an object with get(timeout) to mimic Future
        class _Fut:
            def get(self, timeout: float | int = 5):
                self_inner = self
                remaining = ck.flush(timeout)
                if remaining != 0:
                    raise TimeoutError("produce not fully flushed")
                return None

        ck = self._ck
        return _Fut()

    def flush(self, timeout: float | int = 5):
        return self._ck.flush(timeout)

    def close(self):
        try:
            self._ck.flush(5)
        except Exception:
raise NotImplementedError("Placeholder removed per VIBE rules")


def make_producer() -> _ProducerShim:  # pragma: no cover - integration path
    # Strict: no disable flag pathway; Kafka must be reachable.
    ck = CKProducer({"bootstrap.servers": _bootstrap_url(), "compression.type": "none"})
    return _ProducerShim(ck)


@lru_cache(maxsize=32)
def get_serde(schema_name: str) -> Optional[AvroSerde]:
    """Get Avro serde for schema with caching."""
    if load_schema is None or AvroSerde is None:
        return None
    try:
        return AvroSerde(load_schema(schema_name))  # type: ignore[arg-type]
    except Exception:  # pragma: no cover
        return None


def encode(record: Dict[str, Any], schema_name: Optional[str]) -> bytes:
    """Encode record Avro-only; raise if serde unavailable."""
    if not schema_name:
        raise ValueError("encode: schema_name required in strict mode")
    serde = get_serde(schema_name)
    if serde is None:
        raise RuntimeError(f"encode: Avro serde unavailable for schema {schema_name}")
    return serde.serialize(record)


def decode(data: bytes, schema_name: Optional[str] = None) -> Dict[str, Any]:
    """Decode data Avro-only; raise if serde unavailable."""
    if not schema_name:
        raise ValueError("decode: schema_name required in strict mode")
    serde = get_serde(schema_name)
    if serde is None:
        raise RuntimeError(f"decode: Avro serde unavailable for schema {schema_name}")
    return serde.deserialize(data)


# Shared topic definitions - consolidated from ROADMAP
TOPICS = {
    "state": "cog.state.updates",
    "agent": "cog.agent.updates",
    "action": "cog.action.updates",
    "next": "cog.next.events",
    "soma_state": "soma.belief.state",
    "soma_agent": "soma.belief.agent",
    "soma_action": "soma.belief.action",
    "global_frame": "cog.global.frame",
    "segments": "cog.segments",
    "reward": "cog.reward.events",
    "config": "cog.config.updates",
    "integrator_context": "soma.integrator.context",
    "integrator_context_shadow": "cog.integrator.context.shadow",
    # Roadmap drift & calibration telemetry topics
    "fusion_drift": "cog.fusion.drift.events",
    "fusion_rollback": "cog.fusion.rollback.events",
    "predictor_calibration": "cog.predictor.calibration",
}
