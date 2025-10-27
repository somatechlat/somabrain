"""Centralised configuration for SomaBrain and shared infra.

This module mirrors the pattern used by other services in the SomaStack.
It provides a single ``Settings`` class (pydantic ``BaseSettings``) that
loads values from the canonical ``.env`` file or the environment. All new code
should import ``Settings`` from here instead of calling ``os.getenv`` directly.

The implementation is deliberately permissive – existing code that still
reads environment variables will continue to work because the default values
fallback to the current variables.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Any

BaseSettings: Any  # forward-declare for mypy
try:
    # pydantic v2 moved BaseSettings to the pydantic-settings package. Prefer
    # that when available to maintain the previous BaseSettings behaviour.
    import pydantic_settings as _ps  # type: ignore
    from pydantic import Field
    BaseSettings = _ps.BaseSettings  # type: ignore[attr-defined,assignment]
except Exception:  # pragma: no cover - fallback for older envs
    from pydantic import BaseSettings as _BS, Field
    BaseSettings = _BS  # type: ignore[assignment]


_TRUE_VALUES = {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return raw.strip().lower() in _TRUE_VALUES
    except Exception:
        return default


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default


class Settings(BaseSettings):
    """Application‑wide settings.

    The fields correspond to the environment variables that SomaBrain already
    uses.  ``env_file`` points at the generated ``.env`` so developers can run
    the service locally without manually exporting each variable.
    """

    # Core infra -----------------------------------------------------------
    # Use plain strings for DSNs to remain permissive across environments
    # (the test/dev envs use sqlite:// which PostgresDsn would reject).
    postgres_dsn: str = Field(
        default_factory=lambda: os.getenv(
            "SOMABRAIN_POSTGRES_DSN", "sqlite:///./data/somabrain.db"
        )
    )
    redis_url: str = Field(
        default_factory=lambda: os.getenv("SOMABRAIN_REDIS_URL")
        or os.getenv("REDIS_URL")
        or ""
    )
    kafka_bootstrap_servers: str = Field(
        default_factory=lambda: os.getenv("SOMABRAIN_KAFKA_URL")
        or os.getenv("KAFKA_BOOTSTRAP_SERVERS")
        or ""
    )

    memory_http_endpoint: str = Field(
        default_factory=lambda: os.getenv("SOMABRAIN_MEMORY_HTTP_ENDPOINT")
        or os.getenv("MEMORY_SERVICE_URL")
        or ""
    )
    memory_http_token: Optional[str] = Field(
        default=os.getenv("SOMABRAIN_MEMORY_HTTP_TOKEN")
    )
    http_max_connections: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_HTTP_MAX_CONNS", 64)
    )
    http_keepalive_connections: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_HTTP_KEEPALIVE", 32)
    )
    http_retries: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_HTTP_RETRIES", 1)
    )

    auth_service_url: Optional[str] = Field(
        default=os.getenv("SOMABRAIN_AUTH_SERVICE_URL")
    )
    auth_service_api_key: Optional[str] = Field(
        default=os.getenv("SOMABRAIN_AUTH_SERVICE_API_KEY")
    )

    # Auth / JWT -----------------------------------------------------------
    jwt_secret: Optional[str] = Field(default=os.getenv("SOMABRAIN_JWT_SECRET"))
    # Use str for path to avoid mypy complaining about default type; callers
    # can wrap with Path when needed.
    jwt_public_key_path: Optional[str] = Field(
        default=os.getenv("SOMABRAIN_JWT_PUBLIC_KEY_PATH")
    )

    # Feature flags --------------------------------------------------------
    force_full_stack: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_FORCE_FULL_STACK", False)
    )
    require_external_backends: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS", False)
    )
    require_memory: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_REQUIRE_MEMORY", True)
    )
    disable_auth: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_DISABLE_AUTH", False)
    )
    mode: str = Field(default=os.getenv("SOMABRAIN_MODE", "enterprise"))
    minimal_public_api: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_MINIMAL_PUBLIC_API", False)
    )
    predictor_provider: str = Field(
        default=os.getenv("SOMABRAIN_PREDICTOR_PROVIDER", "").strip().lower() or "stub"
    )
    allow_backend_fallbacks: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_ALLOW_BACKEND_FALLBACKS", False)
    )
    allow_backend_auto_fallbacks: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_ALLOW_BACKEND_AUTO_FALLBACKS", False)
    )
    relax_predictor_ready: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_RELAX_PREDICTOR_READY", False)
    )

    # OPA -----------------------------------------------------------------------------
    opa_url: str = Field(
        default=os.getenv("SOMABRAIN_OPA_URL")
        or os.getenv("SOMA_OPA_URL")
        or ""
    )
    opa_timeout_seconds: float = Field(
        default_factory=lambda: _float_env("SOMA_OPA_TIMEOUT", 2.0)
    )
    opa_fail_closed: bool = Field(
        default_factory=lambda: _bool_env("SOMA_OPA_FAIL_CLOSED", False)
    )

    # Memory client feature toggles ---------------------------------------------------
    memory_enable_weighting: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_MEMORY_ENABLE_WEIGHTING", False)
    )
    memory_phase_priors: str = Field(
        default=os.getenv("SOMABRAIN_MEMORY_PHASE_PRIORS", "")
    )
    memory_quality_exp: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_MEMORY_QUALITY_EXP", 1.0)
    )
    memory_fast_ack: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_MEMORY_FAST_ACK", False)
    )
    memory_db_path: str = Field(
        default=os.getenv("MEMORY_DB_PATH", "./data/memory.db")
    )
    docker_memory_fallback: Optional[str] = Field(
        default=os.getenv("SOMABRAIN_DOCKER_MEMORY_FALLBACK")
    )

    learning_rate_dynamic: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_LEARNING_RATE_DYNAMIC", False)
    )
    debug_memory_client: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_DEBUG_MEMORY_CLIENT", False)
    )
    allow_local_mirrors: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_ALLOW_LOCAL_MIRRORS", True)
    )

    # --- Mode-derived views (read-only, not sourced from env) ---------------------
    # These computed properties provide a single source of truth for behavior
    # by SOMABRAIN_MODE without mutating legacy flags. Existing code continues
    # to read disable_auth/require_external_backends until migrated in Sprint 2.

    @property
    def mode_normalized(self) -> str:
        """Normalized mode name in {dev, staging, prod}. Unknown maps to prod.

        Historically, the default was "enterprise"; we treat that as prod.
        """
        try:
            m = (self.mode or "").strip().lower()
        except Exception:
            m = ""
        if m in ("dev", "development"):  # allow synonyms
            return "dev"
        if m in ("stage", "staging"):
            return "staging"
        # enterprise/main/prod/empty -> prod
        return "prod"

    @property
    def mode_api_auth_enabled(self) -> bool:
        """Whether API auth should be enabled under the current mode.

        - dev: False (policy relaxations for local development)
        - staging: True
        - prod: True
        """
        m = self.mode_normalized
        return m != "dev"

    @property
    def mode_require_external_backends(self) -> bool:
        """Require real backends (no stubs) across all modes by policy.

        This mirrors the "no mocks" requirement and prevents silent fallbacks.
        """
        return True

    @property
    def mode_memstore_auth_required(self) -> bool:
        """Whether memstore HTTP calls must carry a token.

        - dev: True (dev token or approved proxy)
        - staging: True
        - prod: True
        """
        return True

    @property
    def mode_opa_fail_closed(self) -> bool:
        """Whether OPA evaluation should fail-closed by mode.

        - dev: False (allow-dev bundle; permissive)
        - staging: True
        - prod: True
        """
        return self.mode_normalized != "dev"

    @property
    def mode_log_level(self) -> str:
        """Recommended root log level by mode."""
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
        """List of deprecation notices derived from env usage.

        We do not mutate legacy flags here; we only surface guidance so logs
        can point developers to SOMABRAIN_MODE as the source of truth.
        """
        notes: list[str] = []
        try:
            if os.getenv("SOMABRAIN_FORCE_FULL_STACK") is not None:
                notes.append(
                    "SOMABRAIN_FORCE_FULL_STACK is deprecated; use SOMABRAIN_MODE with mode_require_external_backends policy."
                )
        except Exception:
            pass
        try:
            if os.getenv("SOMABRAIN_DISABLE_AUTH") is not None:
                notes.append(
                    "SOMABRAIN_DISABLE_AUTH is deprecated; auth enablement is derived from SOMABRAIN_MODE (mode_api_auth_enabled)."
                )
        except Exception:
            pass
        # Warn on unknown modes
        try:
            raw = (self.mode or "").strip().lower()
            if raw and raw not in ("dev", "development", "stage", "staging", "prod", "enterprise"):
                notes.append(
                    f"Unknown SOMABRAIN_MODE='{self.mode}' -> treating as 'prod'."
                )
        except Exception:
            pass
        return notes

    # Pydantic v2 uses `model_config` (a dict) for configuration. Make the
    # settings loader permissive: allow extra environment variables and keep
    # case-insensitive env names. The `env_file` points to the canonical `.env`.
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "allow",
    }


# Export a singleton – mirrors the historic pattern used throughout the
# codebase (``settings = Settings()``).
settings = Settings()
