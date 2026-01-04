"""Learner Online service.

Consumes next-event feedback from Kafka, computes regret, updates metrics, and
emits configuration updates. Designed for production use with the real transport
and per-tenant overrides.
"""

from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional

import yaml

from django.conf import settings
from common.logging import logger
from somabrain.metrics import (
    LEARNER_EVENTS_CONSUMED,
    LEARNER_EVENTS_FAILED,
    LEARNER_EVENTS_PRODUCED,
    LEARNER_EVENT_LATENCY,
)
from somabrain.services.learner_dlq import LearnerDLQ

__all__ = ["LearnerService"]


class LearnerService:
    """A lightweight learner service for handling next‑event regret and config.

    The implementation focuses on the parts exercised by the test suite.  It
    loads tenant overrides from a YAML file (if the environment variable is set)
    and provides two internal helper methods:

    * ``_observe_next_event`` – records regret on a gauge.
    * ``_emit_cfg`` – emits a configuration update with a decayed ``tau``.
    """

    def __init__(self) -> None:
        # Load tenant overrides from the optional YAML file.
        """Initialize the instance."""

        self._tenant_overrides: Dict[str, Dict[str, Any]] = {}
        overrides_path = settings.SOMABRAIN_LEARNING_TENANTS_FILE
        if overrides_path:
            try:
                with open(overrides_path, "r", encoding="utf-8") as f:
                    self._tenant_overrides = yaml.safe_load(f) or {}
            except Exception as exc:  # pragma: no cover – defensive
                logger.exception("Failed to load learner tenant overrides: %s", exc)

        # Producer is set by the run loop or injected by tests.
        self._producer: Any = None
        # Gauge for next‑event regret – created lazily.  Tests may monkey‑patch.
        self._g_next_regret: Optional[Any] = None
        # Track last processed timestamp per tenant for health/lag metrics
        self._last_seen_ts: Dict[str, float] = {}

        # Settings singleton for topic names.
        self._settings = settings
        self._dlq = LearnerDLQ()

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def run(self) -> None:  # pragma: no cover – heavy I/O
        """Start the learner event loop against the real Kafka transport.

        Fail fast when Kafka bootstrap or topics are not configured or when
        ``confluent_kafka`` is not installed. This avoids the silent no‑op
        behavior of earlier fallback implementations.
        """
        # Use centralized Settings for Kafka bootstrap; no env fallback needed.
        bootstrap = getattr(self._settings, "kafka_bootstrap_servers", "")
        if not bootstrap:
            raise RuntimeError(
                "LearnerService requires Kafka bootstrap servers "
                "(set SOMABRAIN_KAFKA_URL or kafka_bootstrap_servers)."
            )
        # Use Settings for the next-event topic; fallback handled by Settings default.
        topic_next = getattr(self._settings, "topic_next_event", None)
        topic_cfg = getattr(
            self._settings, "topic_config_updates", "cog.config.updates"
        )
        try:
            import confluent_kafka as ck
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "confluent_kafka is required for LearnerService.run(); install the dependency."
            ) from exc

        consumer = ck.Consumer(
            {
                "bootstrap.servers": bootstrap,
                "group.id": "somabrain-learner",
                "enable.auto.commit": False,
                "auto.offset.reset": "earliest",
                "enable.auto.offset.store": False,
                "enable.partition.eof": True,
                "retries": 3,
                "retry.backoff.ms": 200,
            }
        )
        producer = ck.Producer(
            {
                "bootstrap.servers": bootstrap,
                "enable.idempotence": True,
                "acks": "all",
                "linger.ms": 5,
                "batch.num.messages": 500,
            }
        )
        self._producer = producer
        consumer.subscribe([topic_next])
        logger.info(
            "LearnerService consuming %s and emitting %s", topic_next, topic_cfg
        )

        while True:
            msg = consumer.poll(1.0)
            if msg is None:
                continue
            if msg.error():
                logger.error("Kafka error: %s", msg.error())
                continue
            try:
                payload = msg.value()
                event = json.loads(payload)
                self._process_event(event)
                consumer.store_offsets(msg)
                consumer.commit(msg)
            except Exception as exc:
                logger.exception("Failed to process next_event message: %s", exc)
                try:
                    self._dlq.record(event if isinstance(event, dict) else {}, str(exc))
                except Exception as dlq_exc:
                    logger.warning("Failed to record to DLQ: %s", dlq_exc)

    # ---------------------------------------------------------------------
    # Internal helpers used by the test suite
    # ---------------------------------------------------------------------
    def _process_event(self, event: Dict[str, Any]) -> None:
        """Validate and process a ``next_event`` payload; emit metrics."""
        t_start = time.perf_counter()
        tenant = str(event.get("tenant") or "default")
        try:
            confidence = float(event.get("confidence", 0.0))
        except Exception as exc:
            LEARNER_EVENTS_FAILED.labels(tenant_id=tenant, phase="parse").inc()
            raise ValueError("confidence missing or non-numeric") from exc
        if not 0.0 <= confidence <= 1.0:
            LEARNER_EVENTS_FAILED.labels(tenant_id=tenant, phase="bounds").inc()
            raise ValueError("confidence out of bounds [0,1]")

        regret = 1.0 - confidence

        # Lazily create the gauge if it does not exist; fail fast if metrics missing.
        if self._g_next_regret is None:
            from somabrain.metrics import soma_next_event_regret

            self._g_next_regret = soma_next_event_regret

        # Idempotency: skip if already seen event_id
        event_id = str(event.get("event_id") or "")
        if event_id:
            if not hasattr(self, "_seen"):
                self._seen = set()
            if event_id in self._seen:
                return
            self._seen.add(event_id)

        try:
            gauge = self._g_next_regret
            if hasattr(gauge, "labels"):
                gauge.labels(tenant_id=tenant).set(regret)
            else:
                gauge.set(regret)
        except Exception:  # pragma: no cover – defensive logging
            LEARNER_EVENTS_FAILED.labels(tenant_id=tenant, phase="gauge").inc()
            raise

        LEARNER_EVENTS_CONSUMED.labels(tenant_id=tenant).inc()
        self._last_seen_ts[tenant] = time.time()
        self._emit_cfg(
            tenant,
            tau=float(event.get("tau", 1.0)),
            lr=float(event.get("lr", 0.0)),
            event_id=event_id or None,
        )
        elapsed = time.perf_counter() - t_start
        LEARNER_EVENT_LATENCY.labels(tenant_id=tenant).observe(elapsed)

    def _emit_cfg(
        self, tenant: str, tau: float, lr: float, event_id: str | None = None
    ) -> None:
        """Emit a configuration update for *tenant*.

        The ``tau`` value is adjusted by the tenant‑specific ``tau_decay_rate``
        (defaulting to ``0`` if not provided).  The resulting ``exploration_temp``
        is sent as a JSON‑encoded payload to the ``topic_config_updates`` Kafka
        topic.  The producer's ``produce`` method is called with a callback that
        logs delivery results.
        """
        # Apply decay if an override exists.
        decay_rate = (
            self._tenant_overrides.get(tenant, {}).get("tau_decay_rate", 0.0) or 0.0
        )
        try:
            decay_rate = float(decay_rate)
        except Exception:
            decay_rate = 0.0
        new_tau = tau * (1.0 - decay_rate)

        payload_dict = {
            "exploration_temp": new_tau,
            "learning_rate": lr,
            "tenant": tenant,
        }
        if event_id:
            payload_dict["event_id"] = event_id
        payload_bytes = json.dumps(payload_dict).encode("utf-8")

        topic = getattr(self._settings, "topic_config_updates", "cog.config.updates")

        def _delivery_report(err: Optional[Exception], msg: Any) -> None:
            """Execute delivery report.

            Args:
                err: The err.
                msg: The msg.
            """

            if err is not None:
                logger.error("Failed to deliver config update: %s", err)
            else:
                logger.info(
                    "Config update delivered to %s [partition=%s, offset=%s]",
                    topic,
                    getattr(msg, "partition", lambda: None)(),
                    getattr(msg, "offset", lambda: None)(),
                )

        # Guard against a missing producer.
        if self._producer is None:
            raise RuntimeError("LearnerService producer is not configured.")
        try:
            self._producer.produce(topic, payload_bytes, callback=_delivery_report)
            LEARNER_EVENTS_PRODUCED.labels(tenant_id=tenant).inc()
            if hasattr(self._producer, "flush"):
                self._producer.flush()
            # Update lag gauge post-publish
            from somabrain.metrics import LEARNER_LAG_SECONDS

            last = self._last_seen_ts.get(tenant, time.time())
            LEARNER_LAG_SECONDS.labels(tenant_id=tenant).set(
                max(0.0, time.time() - last)
            )
        except Exception as exc:  # pragma: no cover – defensive
            LEARNER_EVENTS_FAILED.labels(tenant_id=tenant, phase="produce").inc()
            logger.exception("Error emitting config update: %s", exc)
