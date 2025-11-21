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
    """Parse an integer environment variable safely.

    The function strips any trailing ``#`` comment (e.g. ``"100 # comment"``)
    before attempting conversion. If conversion fails, the provided ``default``
    is returned.
    """
    raw = os.getenv(name, str(default))
    # Remove anything after a comment marker
    raw = raw.split("#", 1)[0].strip()
    try:
        return int(raw)
    except Exception:
        return default


def _bool_env(name: str, default: bool) -> bool:
    """Parse a boolean environment variable safely.

    Supports typical truthy strings and strips comments.
    """
    raw = os.getenv(name)
    if raw is None:
        return default
    raw = raw.split("#", 1)[0].strip()
    try:
        return raw.lower() in _TRUE_VALUES
    except Exception:
        return default


def _float_env(name: str, default: float) -> float:
    """Parse a float environment variable safely, stripping comments."""
    raw = os.getenv(name, str(default))
    raw = raw.split("#", 1)[0].strip()
    try:
        return float(raw)
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
        default_factory=lambda: _bool_env("SOMABRAIN_FORCE_FULL_STACK", True)
    )
    require_external_backends: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS", True)
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

    # Circuit‑breaker defaults ------------------------------------------------
    circuit_failure_threshold: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_CIRCUIT_FAILURE_THRESHOLD", 3)
    )
    circuit_reset_interval: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_CIRCUIT_RESET_INTERVAL", 60.0)
    )
    # Optional cooldown between successive reset attempts (seconds). Zero disables extra cooldown.
    circuit_cooldown_interval: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_CIRCUIT_COOLDOWN_INTERVAL", 0.0)
    )

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

    # Global learning/feature toggles ------------------------------------------------
    enable_advanced_learning: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_ENABLE_ADVANCED_LEARNING", True)
    )

    # Predictor / integrator configuration -----------------------------------
    predictor_alpha: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_PREDICTOR_ALPHA", 2.0)
    )
    integrator_health_port: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_INTEGRATOR_HEALTH_PORT", 9015)
    )
    integrator_softmax_temperature: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_INTEGRATOR_TEMPERATURE", 1.0)
    )
    enable_cog_threads: bool = Field(
        default_factory=lambda: _bool_env("ENABLE_COG_THREADS", True)
    )

    # Segmentation thresholds and health port --------------------------------
    segment_grad_threshold: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SEGMENT_GRAD_THRESH", 0.2)
    )
    segment_hmm_threshold: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SEGMENT_HMM_THRESH", 0.6)
    )
    segment_health_port: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_SEGMENTATION_HEALTH_PORT", 9016)
    )

    # Retrieval/adaptive weights (dynamic defaults) --------------------------
    retrieval_alpha: float = Field(default_factory=lambda: _float_env("SOMABRAIN_RETRIEVAL_ALPHA", 1.0))
    retrieval_beta: float = Field(default_factory=lambda: _float_env("SOMABRAIN_RETRIEVAL_BETA", 0.2))
    retrieval_gamma: float = Field(default_factory=lambda: _float_env("SOMABRAIN_RETRIEVAL_GAMMA", 0.1))
    retrieval_tau: float = Field(default_factory=lambda: _float_env("SOMABRAIN_RETRIEVAL_TAU", 0.7))
    retrieval_recency_half_life: float = Field(default_factory=lambda: _float_env("SOMABRAIN_RECENCY_HALF_LIFE", 60.0))
    retrieval_recency_sharpness: float = Field(default_factory=lambda: _float_env("SOMABRAIN_RECENCY_SHARPNESS", 1.2))
    retrieval_recency_floor: float = Field(default_factory=lambda: _float_env("SOMABRAIN_RECENCY_FLOOR", 0.05))
    retrieval_density_target: float = Field(default_factory=lambda: _float_env("SOMABRAIN_DENSITY_TARGET", 0.2))
    retrieval_density_floor: float = Field(default_factory=lambda: _float_env("SOMABRAIN_DENSITY_FLOOR", 0.6))
    retrieval_density_weight: float = Field(default_factory=lambda: _float_env("SOMABRAIN_DENSITY_WEIGHT", 0.35))
    retrieval_tau_min: float = Field(default_factory=lambda: _float_env("SOMABRAIN_TAU_MIN", 0.4))
    retrieval_tau_max: float = Field(default_factory=lambda: _float_env("SOMABRAIN_TAU_MAX", 1.2))
    retrieval_tau_increment_up: float = Field(default_factory=lambda: _float_env("SOMABRAIN_TAU_INC_UP", 0.1))
    retrieval_tau_increment_down: float = Field(default_factory=lambda: _float_env("SOMABRAIN_TAU_INC_DOWN", 0.05))
    retrieval_dup_ratio_threshold: float = Field(default_factory=lambda: _float_env("SOMABRAIN_DUP_RATIO_THRESHOLD", 0.5))

    # Neuromodulator defaults (centralized, overridable) ---------------------
    neuromod_dopamine_base: float = Field(default_factory=lambda: _float_env("SOMABRAIN_NEURO_DOPAMINE_BASE", 0.4))
    neuromod_serotonin_base: float = Field(default_factory=lambda: _float_env("SOMABRAIN_NEURO_SEROTONIN_BASE", 0.5))
    neuromod_noradrenaline_base: float = Field(default_factory=lambda: _float_env("SOMABRAIN_NEURO_NORAD_BASE", 0.0))
    neuromod_acetylcholine_base: float = Field(default_factory=lambda: _float_env("SOMABRAIN_NEURO_ACETYL_BASE", 0.0))
    neuromod_dopamine_min: float = Field(default_factory=lambda: _float_env("SOMABRAIN_NEURO_DOPAMINE_MIN", 0.1))
    neuromod_dopamine_max: float = Field(default_factory=lambda: _float_env("SOMABRAIN_NEURO_DOPAMINE_MAX", 1.0))
    neuromod_serotonin_min: float = Field(default_factory=lambda: _float_env("SOMABRAIN_NEURO_SEROTONIN_MIN", 0.0))
    neuromod_serotonin_max: float = Field(default_factory=lambda: _float_env("SOMABRAIN_NEURO_SEROTONIN_MAX", 1.0))
    neuromod_noradrenaline_min: float = Field(default_factory=lambda: _float_env("SOMABRAIN_NEURO_NORAD_MIN", 0.0))
    neuromod_noradrenaline_max: float = Field(default_factory=lambda: _float_env("SOMABRAIN_NEURO_NORAD_MAX", 0.5))
    neuromod_acetylcholine_min: float = Field(default_factory=lambda: _float_env("SOMABRAIN_NEURO_ACETYL_MIN", 0.0))
    neuromod_acetylcholine_max: float = Field(default_factory=lambda: _float_env("SOMABRAIN_NEURO_ACETYL_MAX", 0.5))
    neuromod_dopamine_lr: float = Field(default_factory=lambda: _float_env("SOMABRAIN_NEURO_DOPAMINE_LR", 0.02))
    neuromod_serotonin_lr: float = Field(default_factory=lambda: _float_env("SOMABRAIN_NEURO_SEROTONIN_LR", 0.015))
    neuromod_noradrenaline_lr: float = Field(default_factory=lambda: _float_env("SOMABRAIN_NEURO_NORAD_LR", 0.01))
    neuromod_acetylcholine_lr: float = Field(default_factory=lambda: _float_env("SOMABRAIN_NEURO_ACETYL_LR", 0.01))
    neuromod_urgency_factor: float = Field(default_factory=lambda: _float_env("SOMABRAIN_NEURO_URGENCY_FACTOR", 0.3))
    neuromod_memory_factor: float = Field(default_factory=lambda: _float_env("SOMABRAIN_NEURO_MEMORY_FACTOR", 0.2))

    # Utility/adaptation defaults ---------------------------------------------
    utility_lambda: float = Field(default_factory=lambda: _float_env("SOMABRAIN_UTILITY_LAMBDA", 1.0))
    utility_mu: float = Field(default_factory=lambda: _float_env("SOMABRAIN_UTILITY_MU", 0.1))
    utility_nu: float = Field(default_factory=lambda: _float_env("SOMABRAIN_UTILITY_NU", 0.05))
    utility_lambda_min: float = Field(default_factory=lambda: _float_env("SOMABRAIN_UTILITY_LAMBDA_MIN", 0.0))
    utility_lambda_max: float = Field(default_factory=lambda: _float_env("SOMABRAIN_UTILITY_LAMBDA_MAX", 5.0))
    utility_mu_min: float = Field(default_factory=lambda: _float_env("SOMABRAIN_UTILITY_MU_MIN", 0.0))
    utility_mu_max: float = Field(default_factory=lambda: _float_env("SOMABRAIN_UTILITY_MU_MAX", 5.0))
    utility_nu_min: float = Field(default_factory=lambda: _float_env("SOMABRAIN_UTILITY_NU_MIN", 0.0))
    utility_nu_max: float = Field(default_factory=lambda: _float_env("SOMABRAIN_UTILITY_NU_MAX", 5.0))
    adaptation_learning_rate: float = Field(default_factory=lambda: _float_env("SOMABRAIN_ADAPT_LR", 0.05))
    adaptation_max_history: int = Field(default_factory=lambda: _int_env("SOMABRAIN_ADAPT_MAX_HISTORY", 1000))
    adaptation_alpha_min: float = Field(default_factory=lambda: _float_env("SOMABRAIN_ADAPT_ALPHA_MIN", 0.1))
    adaptation_alpha_max: float = Field(default_factory=lambda: _float_env("SOMABRAIN_ADAPT_ALPHA_MAX", 5.0))
    adaptation_gamma_min: float = Field(default_factory=lambda: _float_env("SOMABRAIN_ADAPT_GAMMA_MIN", 0.0))
    adaptation_gamma_max: float = Field(default_factory=lambda: _float_env("SOMABRAIN_ADAPT_GAMMA_MAX", 1.0))
    adaptation_lambda_min: float = Field(default_factory=lambda: _float_env("SOMABRAIN_ADAPT_LAMBDA_MIN", 0.1))
    adaptation_lambda_max: float = Field(default_factory=lambda: _float_env("SOMABRAIN_ADAPT_LAMBDA_MAX", 5.0))
    adaptation_mu_min: float = Field(default_factory=lambda: _float_env("SOMABRAIN_ADAPT_MU_MIN", 0.01))
    adaptation_mu_max: float = Field(default_factory=lambda: _float_env("SOMABRAIN_ADAPT_MU_MAX", 5.0))
    adaptation_nu_min: float = Field(default_factory=lambda: _float_env("SOMABRAIN_ADAPT_NU_MIN", 0.01))
    adaptation_nu_max: float = Field(default_factory=lambda: _float_env("SOMABRAIN_ADAPT_NU_MAX", 5.0))
    adaptation_gain_alpha: float = Field(default_factory=lambda: _float_env("SOMABRAIN_ADAPT_GAIN_ALPHA", 1.0))
    adaptation_gain_gamma: float = Field(default_factory=lambda: _float_env("SOMABRAIN_ADAPT_GAIN_GAMMA", -0.5))
    adaptation_gain_lambda: float = Field(default_factory=lambda: _float_env("SOMABRAIN_ADAPT_GAIN_LAMBDA", 1.0))
    adaptation_gain_mu: float = Field(default_factory=lambda: _float_env("SOMABRAIN_ADAPT_GAIN_MU", -0.25))
    adaptation_gain_nu: float = Field(default_factory=lambda: _float_env("SOMABRAIN_ADAPT_GAIN_NU", -0.25))

    # Sleep system (hot-configurable) ----------------------------------------
    enable_sleep_system: bool = Field(default_factory=lambda: _bool_env("SOMABRAIN_ENABLE_SLEEP", True))
    sleep_k0: int = Field(default_factory=lambda: _int_env("SOMABRAIN_SLEEP_K0", 100))
    sleep_t0: float = Field(default_factory=lambda: _float_env("SOMABRAIN_SLEEP_T0", 10.0))
    sleep_tau0: float = Field(default_factory=lambda: _float_env("SOMABRAIN_SLEEP_TAU0", 1.0))
    sleep_eta0: float = Field(default_factory=lambda: _float_env("SOMABRAIN_SLEEP_ETA0", 0.1))
    sleep_lambda0: float = Field(default_factory=lambda: _float_env("SOMABRAIN_SLEEP_LAMBDA0", 0.01))
    sleep_B0: float = Field(default_factory=lambda: _float_env("SOMABRAIN_SLEEP_B0", 0.5))
    sleep_K_min: int = Field(default_factory=lambda: _int_env("SOMABRAIN_SLEEP_K_MIN", 1))
    sleep_t_min: float = Field(default_factory=lambda: _float_env("SOMABRAIN_SLEEP_T_MIN", 0.1))
    sleep_alpha_K: float = Field(default_factory=lambda: _float_env("SOMABRAIN_SLEEP_ALPHA_K", 0.8))
    sleep_alpha_t: float = Field(default_factory=lambda: _float_env("SOMABRAIN_SLEEP_ALPHA_T", 0.5))
    sleep_alpha_tau: float = Field(default_factory=lambda: _float_env("SOMABRAIN_SLEEP_ALPHA_TAU", 0.5))
    sleep_alpha_eta: float = Field(default_factory=lambda: _float_env("SOMABRAIN_SLEEP_ALPHA_ETA", 1.0))
    sleep_beta_B: float = Field(default_factory=lambda: _float_env("SOMABRAIN_SLEEP_BETA_B", 0.5))

    # Predictor / integrator configuration -----------------------------------
    predictor_alpha: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_PREDICTOR_ALPHA", 2.0)
    )
    integrator_health_port: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_INTEGRATOR_HEALTH_PORT", 9015)
    )

    # Segmentation thresholds and health port --------------------------------
    segment_grad_threshold: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SEGMENT_GRAD_THRESH", 0.2)
    )
    segment_hmm_threshold: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SEGMENT_HMM_THRESH", 0.6)
    )
    segment_health_port: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_SEGMENTATION_HEALTH_PORT", 9016)
    )

    # Segmentation configuration -------------------------------------------------
    segment_max_dwell_ms: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_SEGMENT_MAX_DWELL_MS", 0)
    )
    segment_min_gap_ms: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_SEGMENT_MIN_GAP_MS", 250)
    )
    segment_write_gap_threshold_ms: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_SEGMENT_WRITE_GAP_THRESHOLD_MS", 30000)
    )

    # CPD segmentation parameters -----------------------------------------------
    cpd_min_samples: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_CPD_MIN_SAMPLES", 20)
    )
    cpd_z: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_CPD_Z", 4.0)
    )
    cpd_min_gap_ms: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_CPD_MIN_GAP_MS", 1000)
    )
    cpd_min_std: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_CPD_MIN_STD", 0.02)
    )

    # Hazard segmentation parameters --------------------------------------------
    hazard_lambda: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_HAZARD_LAMBDA", 0.02)
    )
    hazard_vol_mult: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_HAZARD_VOL_MULT", 3.0)
    )
    hazard_min_samples: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_HAZARD_MIN_SAMPLES", 20)
    )
    hazard_min_gap_ms: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_HAZARD_MIN_GAP_MS", 1000)
    )
    hazard_min_std: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_HAZARD_MIN_STD", 0.02)
    )

    # Consumer group for segmentation service -----------------------------------
    segmentation_consumer_group: str = Field(
        default=os.getenv("SOMABRAIN_CONSUMER_GROUP", "segmentation-service")
    )
    default_tenant: str = Field(
        default=os.getenv("SOMABRAIN_DEFAULT_TENANT", "public")
    )
    host: str = Field(
        default=os.getenv("SOMABRAIN_HOST", "0.0.0.0")
    )
    # Service name for observability – used as a default when tracing is
    # initialised without an explicit name.
    service_name: str = Field(
        default=os.getenv("SOMABRAIN_SERVICE_NAME", "somabrain")
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
    topic_next_event: str = Field(
        default=os.getenv("SOMABRAIN_TOPIC_NEXT_EVENT", "cog.next_event")
    )
    topic_state_updates: str = Field(
        default=os.getenv("SOMABRAIN_TOPIC_STATE_UPDATES", "cog.state.updates")
    )
    topic_agent_updates: str = Field(
        default=os.getenv("SOMABRAIN_TOPIC_AGENT_UPDATES", "cog.agent.updates")
    )
    topic_action_updates: str = Field(
        default=os.getenv("SOMABRAIN_TOPIC_ACTION_UPDATES", "cog.action.updates")
    )
    topic_global_frame: str = Field(
        default=os.getenv("SOMABRAIN_TOPIC_GLOBAL_FRAME", "cog.global.frame")
    )
    topic_segments: str = Field(
        default=os.getenv("SOMABRAIN_TOPIC_SEGMENTS", "cog.segments")
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
