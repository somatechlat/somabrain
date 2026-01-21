"""Centralized mode configuration for SomaBrain.

Single source of truth for deployment modes and derived policies.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from django.conf import settings


class DeploymentMode(str, Enum):
    """Deploymentmode class implementation."""

    DEV = "dev"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass(frozen=True)
class DeploymentProfile:
    """Immutable deployment profile derived from mode."""

    mode: DeploymentMode
    auth_enabled: bool
    opa_fail_closed: bool
    require_external_backends: bool
    require_memory: bool
    log_level: str
    min_replicas: int
    persistence_enabled: bool


class ModeConfig:
    """Central mode configuration with strict validation."""

    PROFILES = {
        DeploymentMode.DEV: DeploymentProfile(
            mode=DeploymentMode.DEV,
            auth_enabled=False,
            opa_fail_closed=False,
            require_external_backends=True,
            require_memory=True,
            log_level="DEBUG",
            min_replicas=1,
            persistence_enabled=False,
        ),
        DeploymentMode.STAGING: DeploymentProfile(
            mode=DeploymentMode.STAGING,
            auth_enabled=True,
            opa_fail_closed=True,
            require_external_backends=True,
            require_memory=True,
            log_level="INFO",
            min_replicas=2,
            persistence_enabled=True,
        ),
        DeploymentMode.PRODUCTION: DeploymentProfile(
            mode=DeploymentMode.PRODUCTION,
            auth_enabled=True,
            opa_fail_closed=True,
            require_external_backends=True,
            require_memory=True,
            log_level="WARNING",
            min_replicas=3,
            persistence_enabled=True,
        ),
    }

    def __init__(self, mode_str: str | None = None):
        """Initialize the instance."""

        mode_str = mode_str or settings.SOMABRAIN_MODE
        self.mode = self._parse_mode(mode_str)
        self.profile = self.PROFILES[self.mode]
        self._validate()

    def _parse_mode(self, mode: str | None) -> DeploymentMode:
        """Execute parse mode.

        Args:
            mode: The mode.
        """

        m = (mode or "").strip().lower()
        if m in ("dev", "development"):
            return DeploymentMode.DEV
        if m in ("stage", "staging"):
            return DeploymentMode.STAGING
        if m in ("prod", "production", "enterprise", "main"):
            return DeploymentMode.PRODUCTION
        raise ValueError(f"Invalid mode: {mode}. Use dev, staging, or production")

    def _validate(self):
        """Execute validate."""

        if self.mode == DeploymentMode.PRODUCTION and not self.profile.auth_enabled:
            raise ValueError("CRITICAL: Auth cannot be disabled in production")
        if not self.profile.require_external_backends:
            raise ValueError("CRITICAL: External backends required in all modes")


def get_mode_config() -> ModeConfig:
    """Get or create singleton mode config."""
    global _MODE_CONFIG
    if _MODE_CONFIG is None:
        _MODE_CONFIG = ModeConfig()
    return _MODE_CONFIG


_MODE_CONFIG: ModeConfig | None = None
