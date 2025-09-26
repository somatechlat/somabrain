"""Minimal audit producer with JSONL fallback.

This module provides a simple `AuditProducer` that will try to send
messages to a Kafka topic using kafka-python. If Kafka is unavailable
or configuration isn't provided, messages are appended to a local
JSONL file as a durable fallback.
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
        journal_path: str = "./audit.journal.jsonl",
    ):
        self.topic = topic
        self.journal_path = journal_path
        self.kafka_bootstrap = kafka_bootstrap
        self._producer = None
        if kafka_bootstrap and KAFKA_AVAILABLE:
            try:
                self._producer = KafkaProducer(
                    bootstrap_servers=[kafka_bootstrap],
                    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                )
            except Exception:
                self._producer = None

    def send(self, event: Dict[str, Any], ensure_durable: bool = True) -> None:
        payload = {"ts": time.time(), "event": event}
        # Try Kafka first
        if self._producer:
            try:
                self._producer.send(self.topic, payload)
                # best-effort flush
                if ensure_durable:
                    self._producer.flush(timeout=5)
                return
            except Exception:
                # fall through to JSONL fallback
                pass

        # JSONL fallback
        os.makedirs(os.path.dirname(self.journal_path) or ".", exist_ok=True)
        with open(self.journal_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, default=str) + "\n")


def make_default_producer() -> AuditProducer:
    kafka = os.environ.get("SOMA_KAFKA_BOOTSTRAP")
    journal = os.environ.get("SOMA_AUDIT_JOURNAL", "./audit.journal.jsonl")
    return AuditProducer(
        topic="soma.audit", kafka_bootstrap=kafka, journal_path=journal
    )
