"""Centralised configuration for SomaBrain and shared infra.

This module mirrors the pattern used by other services in the SomaStack.
It provides a single ``Settings`` class (pydantic ``BaseSettings``) that
loads values from the canonical ``.env`` file or the environment. All new code
should import ``Settings`` from here instead of calling ``os.getenv`` directly.

The implementation is deliberately permissive – existing code that still
reads environment variables will continue to work because the default values
default to the current variables.
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
except Exception:  # pragma: no cover - alternative for older envs
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
    # Postgres DSN is required; no SQLite alternative permitted in strict mode.
    postgres_dsn: str = Field(
        default_factory=lambda: os.getenv("SOMABRAIN_POSTGRES_DSN", "")
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
    # Auth is always-on in strict mode; legacy auth toggle removed.
    mode: str = Field(default=os.getenv("SOMABRAIN_MODE", "full-local"))
    minimal_public_api: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_MINIMAL_PUBLIC_API", False)
    )
    predictor_provider: str = Field(
        default=os.getenv("SOMABRAIN_PREDICTOR_PROVIDER", "").strip().lower() or "mahal"
    )
    relax_predictor_ready: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_RELAX_PREDICTOR_READY", False)
    )

    # OPA -----------------------------------------------------------------------------
    opa_url: str = Field(
        default=os.getenv("SOMABRAIN_OPA_URL") or os.getenv("SOMA_OPA_URL") or ""
    )
    opa_timeout_seconds: float = Field(
        default_factory=lambda: _float_env("SOMA_OPA_TIMEOUT", 2.0)
    )
    # OPA posture derived from mode; env flag removed. Use mode_opa_fail_closed.

    # Memory client feature toggles ---------------------------------------------------
    memory_enable_weighting: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_FF_MEMORY_WEIGHTING", False)
        or _bool_env("SOMABRAIN_MEMORY_ENABLE_WEIGHTING", False)
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
    memory_db_path: str = Field(default=os.getenv("MEMORY_DB_PATH", "./data/memory.db"))

    learning_rate_dynamic: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_LEARNING_RATE_DYNAMIC", False)
    )
    debug_memory_client: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_DEBUG_MEMORY_CLIENT", False)
    )
    # Additional environment variables used throughout the codebase
    health_port: Optional[int] = Field(
        default_factory=lambda: _int_env("HEALTH_PORT", 0) if os.getenv("HEALTH_PORT") else None
    )
    default_tenant: str = Field(
        default=os.getenv("SOMABRAIN_DEFAULT_TENANT", "public")
    )
    host: str = Field(
        default=os.getenv("SOMABRAIN_HOST", "0.0.0.0")
    )
    log_config: str = Field(
        default=os.getenv("SOMABRAIN_LOG_CONFIG", "/app/config/logging.yaml")
    )
    constitution_privkey_path: Optional[str] = Field(
        default=os.getenv("SOMABRAIN_CONSTITUTION_PRIVKEY_PATH")
    )
    constitution_signer_id: str = Field(
        default=os.getenv("SOMABRAIN_CONSTITUTION_SIGNER_ID", "default")
    )
    # Additional optional configuration values used by scripts and CI utilities
    reward_port: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_REWARD_PORT", 8083)
    )
    reward_producer_port: int = Field(
        default_factory=lambda: _int_env("REWARD_PRODUCER_PORT", 30183)
    )
    drift_store_path: str = Field(
        default=os.getenv("SOMABRAIN_DRIFT_STORE", "./data/drift/state.json")
    )
    universe: Optional[str] = Field(
        default=os.getenv("SOMA_UNIVERSE")
    )
    # Teach feedback processor configuration
    teach_feedback_proc_port: int = Field(
        default_factory=lambda: _int_env("TEACH_FEEDBACK_PROC_PORT", 8086)
    )
    teach_feedback_proc_group: str = Field(
        default=os.getenv("TEACH_PROC_GROUP", "teach-feedback-proc")
    )
    teach_dedup_cache_size: int = Field(
        default_factory=lambda: int(os.getenv("TEACH_DEDUP_CACHE_SIZE", "512"))
    )
    # Feature flags service configuration
    feature_flags_port: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_FEATURE_FLAGS_PORT", 9697)
    )
    # Tiered memory cleanup configuration
    tiered_memory_cleanup_backend: str = Field(
        default=os.getenv("SOMABRAIN_CLEANUP_BACKEND", "simple")
    )
    tiered_memory_cleanup_topk: int = Field(
        default_factory=lambda: int(os.getenv("SOMABRAIN_CLEANUP_TOPK", "64"))
    )
    tiered_memory_cleanup_hnsw_m: int = Field(
        default_factory=lambda: int(os.getenv("SOMABRAIN_CLEANUP_HNSW_M", "32"))
    )
    tiered_memory_cleanup_hnsw_ef_construction: int = Field(
        default_factory=lambda: int(os.getenv("SOMABRAIN_CLEANUP_HNSW_EF_CONSTRUCTION", "200"))
    )
    tiered_memory_cleanup_hnsw_ef_search: int = Field(
        default_factory=lambda: int(os.getenv("SOMABRAIN_CLEANUP_HNSW_EF_SEARCH", "128"))
    )
    # Topic names used by scripts/CI utilities
    topic_config_updates: str = Field(
        default=os.getenv("SOMABRAIN_TOPIC_CONFIG_UPDATES", "cog.config.updates")
    )
    # Deprecated alternative toggles removed: no local/durable alternatives allowed

    # --- Mode-derived views (read-only, not sourced from env) ---------------------
    # These computed properties provide a single source of truth for behavior
    # by SOMABRAIN_MODE without mutating legacy flags. Existing code continues
    # to read legacy auth settings/require_external_backends until migrated in Sprint 2.

    @property
    def mode_normalized(self) -> str:
        """Normalized mode name in {dev, staging, prod}. Unknown maps to prod.

        Historically, the default was "enterprise"; we treat that as prod.
        """
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
        """Whether API auth should be enabled under the current mode.

        Strict: Always True across all modes.
        """
        try:
            from somabrain.mode import get_mode_config

            # Even if mode declares dev relaxations, enforce auth in strict mode
            _ = get_mode_config()
            return True
        except Exception:
            return True

    @property
    def mode_require_external_backends(self) -> bool:
        """Require real backends (no stubs) across all modes by policy.

        This mirrors the "no mocks" requirement and prevents silent alternatives.
        """
        try:
            from somabrain.mode import get_mode_config

            return get_mode_config().profile.require_external_backends
        except Exception:
            return True

    @property
    def mode_memory_auth_required(self) -> bool:
        """Whether memory-service HTTP calls must carry a token.

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
            legacy_auth_env = os.getenv("SOMABRAIN_AUTH_LEGACY")
            if legacy_auth_env is not None:
                notes.append(
                    "Legacy auth environment variable is deprecated; auth is always required in strict mode."
                )
        except Exception:
            pass
        # Warn on unknown modes
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
