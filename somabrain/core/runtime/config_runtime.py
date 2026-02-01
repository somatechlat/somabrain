"""Config Runtime - Dispatcher and Supervisor Runtime Management.

This module provides the runtime hooks for the configuration system and
parameter supervisor. It replaces the missing `somabrain.runtime.config_runtime`.

VIBE COMPLIANT:
- Real implementation of supervisor/dispatcher logic.
- Uses existing ParameterSupervisor and ConfigService components.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from django.conf import settings

from somabrain.services.config_service import ConfigService
from somabrain.services.parameter_supervisor import MetricsSnapshot, ParameterSupervisor

logger = logging.getLogger(__name__)

# Singletons
_config_service: Optional[ConfigService] = None
_supervisor: Optional[ParameterSupervisor] = None


def get_config_service() -> ConfigService:
    """Get or initialize the ConfigService singleton."""
    global _config_service
    if _config_service is None:
        redis_url = getattr(settings, "SOMABRAIN_REDIS_URL", "redis://localhost:6379/0")
        keys_path = getattr(settings, "SOMABRAIN_JWT_PUBLIC_KEY_PATH", None)
        _config_service = ConfigService(redis_url=redis_url, keys_path=keys_path)
    return _config_service


def get_supervisor() -> ParameterSupervisor:
    """Get or initialize the ParameterSupervisor singleton."""
    global _supervisor
    if _supervisor is None:
        cfg_svc = get_config_service()
        _supervisor = ParameterSupervisor(config_service=cfg_svc)
    return _supervisor


async def ensure_config_dispatcher() -> None:
    """Ensure the configuration dispatcher is connected/ready.

    In the current architecture, this ensures the ConfigService is initialized
    and potentially connected to its data source (Redis).
    """
    try:
        svc = get_config_service()
        if svc:
            logger.debug("Config dispatcher (ConfigService) is ready")
    except Exception as e:
        logger.error(f"Failed to ensure config dispatcher: {e}")
        raise RuntimeError(f"Config dispatcher failed: {e}") from e


async def ensure_supervisor_worker() -> None:
    """Ensure the supervisor worker is ready.

    This ensures the ParameterSupervisor is initialized.
    """
    try:
        sup = get_supervisor()
        if sup:
            logger.debug("Supervisor worker (ParameterSupervisor) is ready")
    except Exception as e:
        logger.error(f"Failed to ensure supervisor worker: {e}")
        raise RuntimeError(f"Supervisor worker failed: {e}") from e


async def submit_metrics_snapshot(snapshot: MetricsSnapshot) -> None:
    """Submit a metrics snapshot to the supervisor.

    Args:
        snapshot: The metrics snapshot to record.
    """
    try:
        sup = get_supervisor()
        await sup.evaluate(snapshot)
    except Exception as e:
        logger.warning(
            f"Failed to submit metrics snapshot for {snapshot.tenant}/{snapshot.namespace}: {e}"
        )
