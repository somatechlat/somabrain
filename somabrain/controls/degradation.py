"""
Cognitive Degradation Manager - Failsafe Operational Logic.
Copyright (C) 2026 SomaTech LAT.

Handles automated health monitoring of memory backends and triggers
graceful degradation states to ensure zero-latency and zero data loss.
"""

import logging
from enum import Enum
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger("somabrain.degradation")


class HealthStatus(Enum):
    NORMAL = "NORMAL"
    LATENCY_WARN = "LATENCY_WARN"
    DEGRADED = "DEGRADED"
    FAILSAFE = "FAILSAFE"


class DegradationManager:
    """Manages cognitive degradation states based on infra health."""

    # Cache keys for health status
    HEALTH_KEY = "brain:health:status"
    LATENCY_KEY = "brain:health:latency"

    def __init__(self) -> None:
        self.latency_threshold = getattr(
            settings, "SOMABRAIN_LATENCY_THRESHOLD", 0.050
        )  # 50ms
        self.last_check = 0
        self.check_interval = 5.0  # Check every 5s

    def get_status(self, tenant: str = "default") -> HealthStatus:
        """Get current health status for a tenant."""
        status_val = cache.get(f"{self.HEALTH_KEY}:{tenant}", HealthStatus.NORMAL.value)
        return HealthStatus(status_val)

    def report_latency(
        self,
        latency: float,
        service: str,
        tenant: str = "default",
    ) -> None:
        """Report observed latency from a specific service client."""
        if latency > self.latency_threshold:
            logger.warning(
                f"High latency detected for service {service}: {latency:.4f}s"
            )
            cache.set(f"{self.LATENCY_KEY}:{tenant}:{service}", latency, 60)
            self._reevaluate_health(tenant)

    def report_error(
        self, service: str, error: Exception, tenant: str = "default"
    ) -> None:
        """Report a service error and promote health to DEGRADED immediately.

        Writes the DEGRADED status to Redis (300s TTL) and, if Kafka publishing
        is enabled via ``SOMABRAIN_DEGRADATION_KAFKA_TOPIC``, enqueues a
        ``degradation.error`` event via the outbox for reliable delivery.
        """
        logger.error("Service error in %s for tenant %s: %s", service, tenant, error)
        cache.set(f"{self.HEALTH_KEY}:{tenant}", HealthStatus.DEGRADED.value, 300)

        kafka_topic = getattr(settings, "SOMABRAIN_DEGRADATION_KAFKA_TOPIC", "")
        if kafka_topic:
            # Write to the transactional outbox. The outbox worker publishes pending
            # rows to Kafka reliably (at-least-once). We use get_or_create with a
            # 5-minute time-bucket so repeated errors for the same service do not
            # violate the (tenant_id, dedupe_key) unique constraint in OutboxEvent.
            import time
            from django.db import IntegrityError
            from somabrain.admin.core.models import OutboxEvent

            bucket = int(time.time() // 300)  # 5-minute window bucket
            dedupe_key = f"degradation.error:{tenant}:{service}:{bucket}"

            try:
                OutboxEvent.objects.get_or_create(
                    tenant_id=tenant,
                    dedupe_key=dedupe_key,
                    defaults={
                        "topic": kafka_topic,
                        "payload": {
                            "event_type": "degradation.error",
                            "tenant": tenant,
                            "service": service,
                            "error": str(error),
                            "status": HealthStatus.DEGRADED.value,
                        },
                        "status": "pending",
                        "retries": 0,
                    },
                )
            except IntegrityError:
                # Race condition: another process wrote the same dedupe_key — safe to ignore.
                logger.debug(
                    "Outbox dedupe hit for degradation event (tenant=%s, service=%s) — skipping.",
                    tenant,
                    service,
                )
            except Exception as outbox_exc:
                # Fail-loud: outbox write failure is a configuration or DB error.
                logger.error(
                    "Failed to write degradation event to outbox (topic=%s): %s",
                    kafka_topic,
                    outbox_exc,
                )

    def _reevaluate_health(self, tenant: str) -> None:
        """Analyze recent latency/error signals and escalate or recover health state.

        Scans all cached latency keys for this tenant. If any service latency
        exceeds the configured threshold, promotes to LATENCY_WARN or DEGRADED.
        Recovery (return to NORMAL) happens automatically after TTL expiry on
        the cache keys (60s for latency, 300s for errors).
        """
        # Collect all latency readings for this tenant from cache
        current = self.get_status(tenant)
        high_latency_services: list[str] = []

        # Read monitored service names from settings — never hardcode infrastructure names.
        # Default covers the four standard SomaBrain dependencies; override via env:
        #   SOMABRAIN_MONITORED_SERVICES=postgresql,redis,milvus,sfm_http,my_custom_svc
        raw = getattr(
            settings, "SOMABRAIN_MONITORED_SERVICES", "postgresql,redis,milvus,sfm_http"
        )
        known_services = [s.strip() for s in raw.split(",") if s.strip()]

        for svc in known_services:
            val = cache.get(f"{self.LATENCY_KEY}:{tenant}:{svc}")
            if val is not None and float(val) > self.latency_threshold:
                high_latency_services.append(svc)

        if not high_latency_services:
            # No active latency signals — recover if currently warned
            if current == HealthStatus.LATENCY_WARN:
                cache.set(f"{self.HEALTH_KEY}:{tenant}", HealthStatus.NORMAL.value, 300)
                logger.info("Health recovered to NORMAL for tenant %s", tenant)
            return

        # Escalate based on number of degraded services
        if len(high_latency_services) >= 2 or current == HealthStatus.DEGRADED:
            new_status = HealthStatus.DEGRADED
        else:
            new_status = HealthStatus.LATENCY_WARN

        if new_status != current:
            cache.set(f"{self.HEALTH_KEY}:{tenant}", new_status.value, 300)
            logger.warning(
                "Health escalated to %s for tenant %s — slow services: %s",
                new_status.value,
                tenant,
                ", ".join(high_latency_services),
            )

    @property
    def is_degraded(self) -> bool:
        """Return whether the default tenant is operating above NORMAL."""
        return self.get_status() != HealthStatus.NORMAL


degradation_manager = DegradationManager()
