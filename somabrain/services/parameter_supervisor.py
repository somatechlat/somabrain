"""Lightweight parameter supervisor for runtime metric feedback.

This module used to house a more elaborate closed‑loop tuner. For the
current stack we keep a minimal, fully functional implementation that:

- accepts metric snapshots from services (via ``MetricsSnapshot``);
- records the latest snapshot per tenant/namespace;
- exposes an ``evaluate`` coroutine that can later be extended to perform
  adaptive config updates through ``ConfigService``.

The implementation avoids hardcoded fallbacks: it stores real data and can
be wired into future tuning logic without changing call sites.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Tuple

from somabrain.presets import get_preset
from somabrain.services.config_service import ConfigService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MetricsSnapshot:
    """Metricssnapshot class implementation."""

    tenant: str
    namespace: str
    metrics: Dict[str, float]
    timestamp_ms: int = field(
        default_factory=lambda: int(time.time() * 1000),
        metadata={"description": "Unix epoch in milliseconds when captured"},
    )


class ParameterSupervisor:
    """Persist and optionally act on incoming metric snapshots."""

    def __init__(self, config_service: ConfigService) -> None:
        """Initialize the instance."""

        self._config_service = config_service
        # Keep the latest snapshot per (tenant, namespace) for observability/debugging.
        self._latest: Dict[Tuple[str, str], MetricsSnapshot] = {}

    def latest(self, tenant: str, namespace: str) -> MetricsSnapshot | None:
        """Return the most recent snapshot for the given scope."""
        return self._latest.get((tenant, namespace))

    async def evaluate(self, snapshot: MetricsSnapshot) -> None:
        """Store the snapshot; hook for future adaptive tuning."""
        key = (snapshot.tenant or "", snapshot.namespace or "")
        self._latest[key] = snapshot
        # Real-time tuning logic can be added here (e.g., adjusting config via ConfigService)
        logger.debug(
            "ParameterSupervisor recorded snapshot for %s/%s: %s",
            snapshot.tenant,
            snapshot.namespace,
            snapshot.metrics,
        )
        # No automatic config mutation yet; keep behaviour deterministic for local runs.

    async def apply_preset(self, tenant: str, preset_name: str, actor: str = "system") -> None:
        """Apply a cognitive preset to a specific tenant.

        Args:
            tenant: The tenant ID (e.g., 'default').
            preset_name: The name of the preset ('stable', 'plastic', 'lateral').
            actor: The entity requesting the change.
        """
        preset = get_preset(preset_name)
        logger.info(
            "Applying preset '%s' to tenant '%s' (actor=%s)",
            preset.name,
            tenant,
            actor,
        )

        # Patch the tenant configuration with the preset's parameters
        await self._config_service.patch_tenant(
            tenant=tenant,
            patch=preset.params,
            actor=actor,
        )



__all__ = ["MetricsSnapshot", "ParameterSupervisor"]
