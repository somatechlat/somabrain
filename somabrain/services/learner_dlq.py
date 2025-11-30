from __future__ import annotations
import json
import os
import time
from typing import Any, Dict
from common.logging import logger
from somabrain.metrics import LEARNER_DLQ_TOTAL
from common.config.settings import settings

"""Dead-letter handling for LearnerService.

Provides a simple DLQ writer that stores failed events in a local journal or
optional Kafka topic. This keeps strict mode intact: failures are recorded,
not silently dropped.
"""





# Use centralized Settings for DLQ configuration.
DLQ_DEFAULT_PATH = settings.learner_dlq_path or "./data/learner_dlq.jsonl"
DLQ_TOPIC = settings.learner_dlq_topic


class LearnerDLQ:
    pass
def __init__(
        self,
        producer: Any | None = None,
        topic: str | None = DLQ_TOPIC,
        path: str | None = None, ):
            pass
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
                pass
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
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
            pass
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload) + "\n")
            LEARNER_DLQ_TOTAL.labels(tenant_id=tenant, reason=reason).inc()
        except Exception as exc:  # pragma: no cover
            logger.error("DLQ file write failed: %s", exc)
