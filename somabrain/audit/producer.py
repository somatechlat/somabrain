"""Kafka-only audit producer (fail-fast).

This module provides a simple `AuditProducer` that publishes audit
events to Kafka. If Kafka is unavailable or misconfigured, attempts to
send will fail immediately (no local disk fallbacks).
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional

try:
    from kafka import KafkaProducer

    KAFKA_AVAILABLE = True
except Exception:
    KAFKA_AVAILABLE = False


class AuditProducer:
    def __init__(
        self,
        topic: str = "soma.audit",
        kafka_bootstrap: Optional[str] = None,
    ):
        self.topic = topic
        self.kafka_bootstrap = kafka_bootstrap
        self._producer = None
        if not kafka_bootstrap:
            raise RuntimeError("Kafka bootstrap is required for AuditProducer")
        if not KAFKA_AVAILABLE:
            raise RuntimeError(
                "kafka-python not available; cannot create AuditProducer"
            )
        try:
            self._producer = KafkaProducer(
                bootstrap_servers=[kafka_bootstrap],
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
        except Exception as exc:
            raise RuntimeError(
                "Failed to create Kafka producer for audit events"
            ) from exc

    def send(self, event: Dict[str, Any], ensure_durable: bool = True) -> None:
        payload = {"ts": time.time(), "event": event}
        if self._producer is None:
            raise RuntimeError("AuditProducer not initialized with Kafka producer")
        fut = self._producer.send(self.topic, payload)
        if ensure_durable:
            # Ensure message is handed to broker within timeout; raise on failure
            fut.get(timeout=5)


def make_default_producer() -> AuditProducer:
    kafka = os.environ.get("SOMA_KAFKA_BOOTSTRAP")
    if not kafka:
        raise RuntimeError("SOMA_KAFKA_BOOTSTRAP not set for audit producer")
    return AuditProducer(topic="soma.audit", kafka_bootstrap=kafka)
