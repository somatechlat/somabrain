"""Modular Settings Package for SomaBrain.

This package provides a unified Settings class that aggregates domain-specific
configuration modules. All modules should import from this package:

    from common.config.settings import settings

The Settings class inherits from all domain-specific mixins to provide a single
source of truth for configuration.
"""

from __future__ import annotations

from typing import Optional

from common.config.settings.base import (
    BaseSettings,
    Field,
    SettingsConfigDict,
    _bool_env,
    _float_env,
    _int_env,
    _str_env,
    _yaml_get,
)
from common.config.settings.infra import InfraSettingsMixin
from common.config.settings.memory import MemorySettingsMixin
from common.config.settings.learning import LearningSettingsMixin
from common.config.settings.auth import AuthSettingsMixin
from common.config.settings.oak import OakSettingsMixin
from common.config.settings.cognitive import CognitiveSettingsMixin

__all__ = [
    "Settings",
    "settings",
    "BaseSettings",
    "Field",
    "SettingsConfigDict",
    "_bool_env",
    "_float_env",
    "_int_env",
    "_str_env",
    "_yaml_get",
]


class Settings(
    InfraSettingsMixin,
    MemorySettingsMixin,
    LearningSettingsMixin,
    AuthSettingsMixin,
    OakSettingsMixin,
    CognitiveSettingsMixin,
):
    """Unified application settings aggregating all domain-specific configurations.

    Configuration precedence (highest to lowest):
    1. Environment variables
    2. .env file
    3. config.yaml
    """

    # Mode-derived properties
    @property
    def mode_normalized(self) -> str:
        """Normalized mode name in {dev, staging, prod}. Unknown maps to prod."""
        try:
            from somabrain.mode import get_mode_config

            return get_mode_config().mode.value
        except Exception:
            m = (self.mode or "").strip().lower()
            if m in ("dev", "development"):
                return "dev"
            if m in ("stage", "staging"):
                return "staging"
            return "prod"

    @property
    def mode_api_auth_enabled(self) -> bool:
        """Whether API auth should be enabled under the current mode."""
        return True

    @property
    def mode_require_external_backends(self) -> bool:
        """Require real backends across all modes by policy."""
        try:
            from somabrain.mode import get_mode_config

            return get_mode_config().profile.require_external_backends
        except Exception:
            return True

    @property
    def mode_memory_auth_required(self) -> bool:
        """Whether memory-service HTTP calls must carry a token."""
        return True

    @property
    def mode_opa_fail_closed(self) -> bool:
        """Whether OPA evaluation should fail-closed by mode."""
        try:
            from somabrain.mode import get_mode_config

            return get_mode_config().profile.opa_fail_closed
        except Exception:
            return self.mode_normalized != "dev"

    @property
    def mode_log_level(self) -> str:
        """Recommended root log level by mode."""
        try:
            from somabrain.mode import get_mode_config

            return get_mode_config().profile.log_level
        except Exception:
            m = self.mode_normalized
            if m == "dev":
                return "DEBUG"
            if m == "staging":
                return "INFO"
            return "WARNING"

    @property
    def mode_opa_policy_bundle(self) -> str:
        """Policy bundle name to use by mode."""
        m = self.mode_normalized
        if m == "dev":
            return "allow-dev"
        if m == "staging":
            return "staging"
        return "prod"

    @property
    def deprecation_notices(self) -> list[str]:
        """List of deprecation notices derived from env usage."""
        notes: list[str] = []
        try:
            if _str_env("SOMABRAIN_FORCE_FULL_STACK") is not None:
                notes.append(
                    "SOMABRAIN_FORCE_FULL_STACK is deprecated; use SOMABRAIN_MODE."
                )
        except Exception:
            pass
        try:
            raw = (self.mode or "").strip().lower()
            if raw and raw not in (
                "dev",
                "development",
                "stage",
                "staging",
                "prod",
                "enterprise",
            ):
                notes.append(
                    f"Unknown SOMABRAIN_MODE='{self.mode}' -> treating as 'prod'."
                )
        except Exception:
            pass
        return notes

    def _env_to_attr(self, name: str) -> str:
        """Best-effort mapping from env var name to Settings attribute."""
        key = name.lower()
        for prefix in ("somabrain_", "soma_", "opa_"):
            if key.startswith(prefix):
                key = key[len(prefix) :]
                break
        key = key.replace("-", "_")
        return key

    def getenv(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Blocked: all call sites must use typed Settings attributes."""
        raise RuntimeError(
            f"settings.getenv('{name}') is prohibited. Replace with Settings attributes."
        )


# Export singleton instance
settings = Settings()
