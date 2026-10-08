"""Cognitive preset application for tenants.

This module applies named cognitive presets (stable/plastic/lateral) to a
tenant's configuration via ``ConfigService``. There is no automatic tuning
loop here: preset application is explicit and actor-attributed. Metric
snapshots are not consumed; a real tuner would be a separate, tested service.
"""

from __future__ import annotations

import logging

from somabrain.admin.core.presets import get_preset
from somabrain.services.config_service import ConfigService

logger = logging.getLogger(__name__)


class ParameterSupervisor:
    """Apply cognitive presets to tenant configuration."""

    def __init__(self, config_service: ConfigService) -> None:
        """Initialize the instance."""

        self._config_service = config_service

    async def apply_preset(
        self, tenant: str, preset_name: str, actor: str = "system"
    ) -> None:
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


__all__ = ["ParameterSupervisor"]
