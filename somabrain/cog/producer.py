from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from somabrain.common.kafka import make_producer, encode


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
        self._producer = None
        bootstrap = _bootstrap_from_env()
        if not bootstrap:
            raise RuntimeError(
                "SOMABRAIN_KAFKA_URL not configured for BeliefUpdatePublisher"
            )
        # Strict: confluent-kafka producer and Avro-only serialization
        self._producer = make_producer()
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
        payload = encode(record, "belief_update")
        self._producer.send(topic, value=payload)
