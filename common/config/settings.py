"""Centralised configuration for SomaBrain and shared infra.

This module mirrors the pattern used by other services in the SomaStack.
It provides a single ``Settings`` class (pydantic ``BaseSettings``) that
loads values from ``.env.local`` or the environment.  All new code should
import ``Settings`` from here instead of calling ``os.getenv`` directly.

The implementation is deliberately permissive – existing code that still
reads environment variables will continue to work because the default values
fallback to the current variables.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

try:
    # pydantic v2 moved BaseSettings to the pydantic-settings package. Prefer
    # that when available to maintain the previous BaseSettings behaviour.
    from pydantic_settings import BaseSettings
    from pydantic import Field
except Exception:  # pragma: no cover - fallback for older envs
    from pydantic import BaseSettings, Field


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
    uses.  ``env_file`` points at the generated ``.env.local`` so developers
    can run the service locally without manually exporting each variable.
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
        default_factory=lambda: os.getenv(
            "SOMABRAIN_REDIS_URL", "redis://localhost:6379/0"
        )
    )
    kafka_bootstrap_servers: str = Field(
        default_factory=lambda: os.getenv(
            "SOMABRAIN_KAFKA_URL", "kafka://localhost:9092"
        )
    )

    memory_http_endpoint: str = Field(
        default_factory=lambda: os.getenv(
            "SOMABRAIN_MEMORY_HTTP_ENDPOINT", "http://localhost:9595"
        )
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
    jwt_public_key_path: Optional[Path] = Field(
        default=os.getenv("SOMABRAIN_JWT_PUBLIC_KEY_PATH")
    )

    # Feature flags --------------------------------------------------------
    force_full_stack: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_FORCE_FULL_STACK", False)
    )
    strict_real: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_STRICT_REAL", False)
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
    strict_real_bypass: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_STRICT_REAL_BYPASS", False)
    )
    strict_real_bypass_automatic: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_STRICT_REAL_BYPASS_AUTOMATIC", False)
    )
    relax_predictor_ready: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_RELAX_PREDICTOR_READY", False)
    )

    # OPA -----------------------------------------------------------------------------
    opa_url: str = Field(default=os.getenv("SOMA_OPA_URL", "http://opa:8181"))
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

    # Pydantic v2 uses `model_config` (a dict) for configuration. Make the
    # settings loader permissive: allow extra environment variables and keep
    # case-insensitive env names. The `env_file` is preserved so `.env.local`
    # will be loaded during local development.
    model_config = {
        "env_file": ".env.local",
        "case_sensitive": False,
        "extra": "allow",
    }


# Export a singleton – mirrors the historic pattern used throughout the
# codebase (``settings = Settings()``).
settings = Settings()
