"""Dead-letter handling for LearnerService.

Provides a simple DLQ writer that stores failed events in a local journal or
optional Kafka topic. This keeps strict mode intact: failures are recorded,
not silently dropped.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional

from common.logging import logger
from somabrain.metrics import LEARNER_DLQ_TOTAL

DLQ_DEFAULT_PATH = os.getenv("SOMABRAIN_LEARNER_DLQ_PATH", "./data/learner_dlq.jsonl")
DLQ_TOPIC = os.getenv("SOMABRAIN_LEARNER_DLQ_TOPIC", "").strip() or None


class LearnerDLQ:
    def __init__(self, producer: Any | None = None, topic: str | None = DLQ_TOPIC, path: str | None = None):
        self.producer = producer
        self.topic = topic
        self.path = path or DLQ_DEFAULT_PATH

    def record(self, event: Dict[str, Any], reason: str) -> None:
        payload = {
            "ts": time.time(),
            "reason": reason,
            "event": event,
        }
        tenant = str(event.get("tenant") or "default")
        if self.producer and self.topic:
            try:
                self.producer.produce(self.topic, json.dumps(payload).encode("utf-8"))
                if hasattr(self.producer, "flush"):
                    self.producer.flush()
                LEARNER_DLQ_TOTAL.labels(tenant_id=tenant, reason=reason).inc()
                return
            except Exception as exc:  # pragma: no cover
                logger.error("DLQ produce failed: %s", exc)
        # Fallback to local append-only file
        path = self.path
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload) + "\n")
            LEARNER_DLQ_TOTAL.labels(tenant_id=tenant, reason=reason).inc()
        except Exception as exc:  # pragma: no cover
            logger.error("DLQ file write failed: %s", exc)
