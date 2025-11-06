from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from kafka import KafkaProducer  # type: ignore


def _bootstrap_from_env() -> Optional[str]:
    url = os.getenv("SOMABRAIN_KAFKA_URL")
    if not url:
        return None
    return url.replace("kafka://", "").strip()


class BeliefUpdatePublisher:
    """Lightweight producer for BeliefUpdate events to cog.<domain>.updates.

    Uses fastavro schemaless serde when available; otherwise, falls back to JSON bytes.
    Requires Kafka to be configured and reachable; does not silently degrade.
    """

    def __init__(self) -> None:
        self.enabled = False
        self._value_serializer = None
        self._producer: Optional[KafkaProducer] = None
        bootstrap = _bootstrap_from_env()
        if not bootstrap:
            raise RuntimeError("SOMABRAIN_KAFKA_URL not configured for BeliefUpdatePublisher")
        # Try Avro first
        try:
            from libs.kafka_cog.avro_schemas import load_schema  # type: ignore
            from libs.kafka_cog.serde import AvroSerde  # type: ignore

            schema = load_schema("belief_update")
            serde = AvroSerde(schema)

            def _ser(record: Dict[str, Any]) -> bytes:
                return serde.serialize(record)

            self._value_serializer = _ser
        except Exception:
            # Fallback to JSON bytes
            import json

            def _ser(record: Dict[str, Any]) -> bytes:
                return json.dumps(record).encode("utf-8")

            self._value_serializer = _ser

        self._producer = KafkaProducer(
            bootstrap_servers=bootstrap,
            acks="1",
            linger_ms=5,
            value_serializer=self._value_serializer,
        )
        self.enabled = True

    @staticmethod
    def _topic(domain: str) -> str:
        d = (domain or "").strip().lower()
        if d not in ("state", "agent", "action"):
            d = "state"
        return f"cog.{d}.updates"

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    def publish(
        self,
        *,
        domain: str,
        delta_error: float,
        confidence: float,
        evidence: Optional[Dict[str, str]] = None,
        posterior: Optional[Dict[str, str]] = None,
        model_ver: str = "unknown",
        latency_ms: int = 0,
        ts: Optional[str] = None,
    ) -> None:
        if not self.enabled or not self._producer:
            raise RuntimeError("BeliefUpdatePublisher not initialized")
        record = {
            "domain": domain if domain in ("state", "agent", "action") else "state",
            "ts": ts or self._now_iso(),
            "delta_error": float(delta_error),
            "confidence": float(confidence),
            "evidence": evidence or {},
            "posterior": posterior or {},
            "model_ver": model_ver,
            "latency_ms": int(latency_ms),
        }
        topic = self._topic(domain)
        self._producer.send(topic, value=record)
