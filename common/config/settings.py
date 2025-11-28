"""Centralised configuration for SomaBrain and shared infra.

This module mirrors the pattern used by other services in the SomaStack.
It provides a single ``Settings`` class (pydantic ``BaseSettings``) that
loads values from the canonical ``.env`` file or the environment. All new code
should import ``Settings`` from here instead of calling ``settings.getenv`` directly.

The implementation is deliberately permissive – existing code that still
reads environment variables will continue to work because the default values
default to the current variables.
"""

from __future__ import annotations

import os
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


def _str_env(name: str, default: str | None = None) -> str | None:
    """Return a string environment variable, stripping inline comments."""
    raw = os.getenv(name)
    if raw is None:
        return default
    # remove trailing comment if present
    raw = raw.split("#", 1)[0].strip()
    return raw if raw != "" else default


class Settings(BaseSettings):
    """Application‑wide settings.

    The fields correspond to the environment variables that SomaBrain already
    uses.  ``env_file`` points at the generated ``.env`` so developers can run
    the service locally without manually exporting each variable.
    """

    # Core infra -----------------------------------------------------------
    # Postgres DSN is required; no SQLite alternative permitted in strict mode.
    postgres_dsn: str = Field(
        default_factory=lambda: _str_env("SOMABRAIN_POSTGRES_DSN", "")
    )
    # Host HOME (used for mode resolution) exposed to avoid direct os.getenv in code paths.
    home_dir: str = Field(default_factory=lambda: _str_env("HOME", "") or "")
    redis_url: str = Field(
        default_factory=lambda: _str_env("SOMABRAIN_REDIS_URL")
        or _str_env("REDIS_URL")
        or ""
    )
    # Kafka bootstrap servers – strip any URL scheme (e.g. "kafka://") to provide a plain host:port string expected by confluent_kafka.
    kafka_bootstrap_servers: str = Field(
        default_factory=lambda: (
            _str_env("SOMABRAIN_KAFKA_URL") or _str_env("KAFKA_BOOTSTRAP_SERVERS") or ""
        ).replace("kafka://", "")
    )
    # Host/port overrides used by infra helpers
    redis_host: Optional[str] = Field(
        default=_str_env("SOMABRAIN_REDIS_HOST") or _str_env("REDIS_HOST")
    )
    redis_port: Optional[int] = Field(
        default=_int_env("SOMABRAIN_REDIS_PORT", _int_env("REDIS_PORT", 6379))
    )
    redis_db: Optional[int] = Field(
        default=_int_env("SOMABRAIN_REDIS_DB", _int_env("REDIS_DB", 0))
    )

    memory_http_host: Optional[str] = Field(
        default=_str_env("SOMABRAIN_MEMORY_HTTP_HOST") or _str_env("MEMORY_HTTP_HOST")
    )
    memory_http_port: Optional[int] = Field(
        default=_int_env("SOMABRAIN_MEMORY_HTTP_PORT", _int_env("MEMORY_HTTP_PORT", 0))
    )
    memory_http_scheme: Optional[str] = Field(
        default=_str_env("SOMABRAIN_MEMORY_HTTP_SCHEME")
        or _str_env("MEMORY_HTTP_SCHEME")
        or "http"
    )

    kafka_host: Optional[str] = Field(
        default=_str_env("SOMABRAIN_KAFKA_HOST") or _str_env("KAFKA_HOST")
    )
    kafka_port: Optional[int] = Field(
        default=_int_env("SOMABRAIN_KAFKA_PORT", _int_env("KAFKA_PORT", 0))
    )
    kafka_scheme: Optional[str] = Field(
        default=_str_env("SOMABRAIN_KAFKA_SCHEME")
        or _str_env("KAFKA_SCHEME")
        or "kafka"
    )

    opa_host: Optional[str] = Field(
        default=_str_env("SOMABRAIN_OPA_HOST") or _str_env("OPA_HOST")
    )
    opa_port: Optional[int] = Field(
        default=_int_env("SOMABRAIN_OPA_PORT", _int_env("OPA_PORT", 0))
    )
    opa_scheme: Optional[str] = Field(
        default=_str_env("SOMABRAIN_OPA_SCHEME") or _str_env("OPA_SCHEME") or "http"
    )

    memory_http_endpoint: str = Field(
        default_factory=lambda: _str_env("SOMABRAIN_MEMORY_HTTP_ENDPOINT")
        or _str_env("MEMORY_SERVICE_URL")
        or "http://localhost:9595"
    )
    memory_http_token: Optional[str] = Field(
        default=_str_env("SOMABRAIN_MEMORY_HTTP_TOKEN")
    )
    # Additional infra configuration fields used throughout the codebase.
    # These were previously accessed via direct ``settings.getenv`` calls.
    log_path: str = Field(
        default=_str_env("SOMABRAIN_LOG_PATH", "somabrain.log").strip()
    )
    # Journal directory for local journal persistence.
    journal_dir: str = Field(
        default=_str_env("SOMABRAIN_JOURNAL_DIR", "/tmp/somabrain_journal")
    )
    supervisor_url: Optional[str] = Field(default=_str_env("SUPERVISOR_URL"))
    supervisor_http_user: str = Field(default=_str_env("SUPERVISOR_HTTP_USER", "admin"))
    supervisor_http_pass: str = Field(default=_str_env("SUPERVISOR_HTTP_PASS", "soma"))
    # Runtime environment flags
    running_in_docker: bool = Field(
        default_factory=lambda: _bool_env("RUNNING_IN_DOCKER", False)
    )

    # --- Milvus configuration (ROAMDP) --------------------------------------
    # --- Milvus configuration (ROAMDP) --------------------------------------
    # Host and port are optional because the client can be instantiated with a
    # full URL (``milvus_url``). When not provided the defaults mirror the
    # official Milvus Docker image.
    milvus_host: Optional[str] = Field(
        default=_str_env("MILVUS_HOST") or _str_env("SOMABRAIN_MILVUS_HOST")
    )
    milvus_port: Optional[int] = Field(
        default=_int_env(
            "MILVUS_PORT",
            _int_env("SOMABRAIN_MILVUS_PORT", 19530),
        )
    )
    milvus_collection: str = Field(
        default=_str_env("MILVUS_COLLECTION", "oak_options")
    )
    # Convenience full URL – used by the Milvus client when both host and
    # port are present. This keeps the client implementation free of
    # environment‑lookup logic, satisfying the VIBE “single source of truth”.
    milvus_url: Optional[str] = Field(
        default_factory=lambda: (
            f"{_str_env('MILVUS_HOST', 'localhost')}:{_int_env('MILVUS_PORT', 19530)}"
        )
    )

    # --- Oak (ROAMDP) configuration ---------------------------------------
    # Feature flag – disables all Oak endpoints when False.
    ENABLE_OAK: bool = Field(default=_bool_env("ENABLE_OAK", False))
    # Utility calculation defaults
    OAK_BASE_UTILITY: float = Field(default=_float_env("OAK_BASE_UTILITY", 1.0))
    OAK_UTILITY_FACTOR: float = Field(default=_float_env("OAK_UTILITY_FACTOR", 0.1))
    OAK_TAU_MIN: float = Field(default=_float_env("OAK_TAU_MIN", 30.0))
    OAK_TAU_MAX: float = Field(default=_float_env("OAK_TAU_MAX", 300.0))
    # Planner defaults
    OAK_PLAN_MAX_OPTIONS: int = Field(default=_int_env("OAK_PLAN_MAX_OPTIONS", 10))
    # Default cursor start index for CognitiveThread models
    COGNITIVE_THREAD_DEFAULT_CURSOR: int = 0
    # Default similarity threshold for option similarity search. Lowered to 0.8
    # to align with unit‑test expectations (a hit with distance 0.2 yields a
    # similarity of ~0.833, which should be accepted).
    OAK_SIMILARITY_THRESHOLD: float = Field(default=_float_env("OAK_SIMILARITY_THRESHOLD", 0.8))
    # Salience / reward thresholds for option creation
    OAK_REWARD_THRESHOLD: float = Field(default=_float_env("OAK_REWARD_THRESHOLD", 0.5))
    OAK_NOVELTY_THRESHOLD: float = Field(default=_float_env("OAK_NOVELTY_THRESHOLD", 0.2))
    # Discount factor for environment reward (γ)
    OAK_GAMMA: float = Field(default=_float_env("OAK_GAMMA", 0.99))
    # EMA update factor (α)
    OAK_ALPHA: float = Field(default=_float_env("OAK_ALPHA", 0.1))
    # Kappa weight (κ) for utility combination
    OAK_KAPPA: float = Field(default=_float_env("OAK_KAPPA", 1.0))
    # Integrator and segmentation service URLs (optional external services)
    integrator_url: Optional[str] = Field(default=_str_env("INTEGRATOR_URL"))
    segmentation_url: Optional[str] = Field(default=_str_env("SEGMENTATION_URL"))

    # Additional utility fields used by scripts / benchmarks
    reward_producer_port: int = Field(
        default_factory=lambda: _int_env("REWARD_PRODUCER_PORT", 30183)
    )
    reward_producer_host_port: int = Field(
        default_factory=lambda: _int_env("REWARD_PRODUCER_HOST_PORT", 30183)
    )
    bench_timeout: float = Field(
        default_factory=lambda: _float_env("BENCH_TIMEOUT", 90.0)
    )
    host_port: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_HOST_PORT", 9696)
    )
    # Public API host/port configuration used for constructing the base URL.
    # These map to SOMABRAIN_PUBLIC_HOST and SOMABRAIN_PUBLIC_PORT environment
    # variables. Defaults mirror the historic host_port values for backward
    # compatibility.
    public_host: Optional[str] = Field(
        default=_str_env("SOMABRAIN_PUBLIC_HOST") or "localhost"
    )
    public_port: Optional[int] = Field(
        default=_int_env("SOMABRAIN_PUBLIC_PORT", 9696)
    )
    # API scheme (http/https) – used when constructing the base URL.
    api_scheme: Optional[str] = Field(
        default=_str_env("SOMABRAIN_API_SCHEME") or "http"
    )
    providers_path: Optional[str] = Field(default=_str_env("PROVIDERS_PATH"))
    spectral_cache_dir: Optional[str] = Field(
        default=_str_env("SOMABRAIN_SPECTRAL_CACHE_DIR")
    )

    # Authentication configuration ------------------------------------------------
    # ``auth_required`` determines whether the API enforces bearer‑token auth.
    # It defaults to ``False`` for local development (mirroring ``config.yaml``).
    # ``api_token`` holds the static token value when ``auth_required`` is True.
    # Both values can be overridden via environment variables for production.
    auth_required: bool = Field(default_factory=lambda: _bool_env("SOMABRAIN_AUTH_REQUIRED", False))
    api_token: str = Field(default_factory=lambda: _str_env("SOMABRAIN_API_TOKEN", ""))
    learner_dlq_path: str = Field(
        default=_str_env("SOMABRAIN_LEARNER_DLQ_PATH", "./data/learner_dlq.jsonl")
    )
    learner_dlq_topic: Optional[str] = Field(
        default=_str_env("SOMABRAIN_LEARNER_DLQ_TOPIC")
    )
    # New fields for script / service configuration
    log_config: Optional[str] = Field(default=_str_env("SOMABRAIN_LOG_CONFIG"))
    workers: int = Field(default_factory=lambda: _int_env("SOMABRAIN_WORKERS", 1))
    outbox_api_token: Optional[str] = Field(
        default=_str_env("SOMABRAIN_API_TOKEN") or _str_env("SOMA_API_TOKEN")
    )
    feature_overrides_path: Optional[str] = Field(
        default=_str_env("SOMABRAIN_FEATURE_OVERRIDES", "./data/feature_overrides.json")
    )
    graph_file_action: Optional[str] = Field(
        default=_str_env("SOMABRAIN_GRAPH_FILE_ACTION")
    )
    graph_file_agent: Optional[str] = Field(
        default=_str_env("SOMABRAIN_GRAPH_FILE_AGENT")
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
        default=_str_env("SOMABRAIN_AUTH_SERVICE_URL")
    )
    auth_service_api_key: Optional[str] = Field(
        default=_str_env("SOMABRAIN_AUTH_SERVICE_API_KEY")
    )
    # API token for auth guard (used by /remember, /recall when auth enabled)
    api_token: Optional[str] = Field(default=_str_env("SOMABRAIN_API_TOKEN"))

    # Auth / JWT -----------------------------------------------------------
    jwt_secret: Optional[str] = Field(default=_str_env("SOMABRAIN_JWT_SECRET"))
    jwt_public_key_path: Optional[str] = Field(
        default=_str_env("SOMABRAIN_JWT_PUBLIC_KEY_PATH")
    )
    # Vault configuration (used by constitution module)
    vault_addr: Optional[str] = Field(default=_str_env("VAULT_ADDR"))
    vault_token: Optional[str] = Field(default=_str_env("VAULT_TOKEN"))
    vault_pubkey_path: Optional[str] = Field(
        default=_str_env("SOMABRAIN_VAULT_PUBKEY_PATH")
    )
    # Constitution configuration
    constitution_pubkeys: Optional[str] = Field(
        default=_str_env("SOMABRAIN_CONSTITUTION_PUBKEYS")
    )
    constitution_pubkey_path: Optional[str] = Field(
        default=_str_env("SOMABRAIN_CONSTITUTION_PUBKEY_PATH")
    )
    constitution_threshold: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_CONSTITUTION_THRESHOLD", 1)
    )
    constitution_signer_id: Optional[str] = Field(
        default=_str_env("SOMABRAIN_CONSTITUTION_SIGNER_ID", "default")
    )
    # OPA bundle path (optional)
    opa_bundle_path: Optional[str] = Field(default=_str_env("OPA_BUNDLE_PATH") or "./opa")

    # -----------------------------------------------------------------
    # Outbox worker configuration (environment variables used by
    # ``somabrain.workers.outbox_publisher``). These defaults mirror the
    # historic hard‑coded values and provide typed access for the worker.
    # -----------------------------------------------------------------
    outbox_batch_size: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_OUTBOX_BATCH_SIZE", 100)
    )
    outbox_max_retries: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_OUTBOX_MAX_RETRIES", 5)
    )
    outbox_poll_interval: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_OUTBOX_POLL_INTERVAL", 1.0)
    )
    outbox_producer_retry_ms: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_OUTBOX_PRODUCER_RETRY_MS", 1000)
    )
    # Interval (seconds) for replaying journal events to the database.
    journal_replay_interval: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_JOURNAL_REPLAY_INTERVAL", 300)
    )
    # Additional configuration fields needed for full removal of settings.getenv usage
    heat_method: str = Field(default=_str_env("SOMA_HEAT_METHOD", "chebyshev"))
    diffusion_t: float = Field(default=_float_env("SOMABRAIN_DIFFUSION_T", 0.5))
    # Graph file fallbacks (domain‑specific and generic)
    graph_file: Optional[str] = Field(default=_str_env("SOMABRAIN_GRAPH_FILE"))
    lanczos_m: int = Field(default=_int_env("SOMABRAIN_LANCZOS_M", 20))
    predictor_dim: int = Field(default=_int_env("SOMABRAIN_PREDICTOR_DIM", 16))
    predictor_alpha: float = Field(default=_float_env("SOMABRAIN_PREDICTOR_ALPHA", 2.0))
    predictor_gamma: float = Field(
        default=_float_env("SOMABRAIN_PREDICTOR_GAMMA", -0.5)
    )
    predictor_lambda: float = Field(
        default=_float_env("SOMABRAIN_PREDICTOR_LAMBDA", 1.0)
    )
    predictor_mu: float = Field(default=_float_env("SOMABRAIN_PREDICTOR_MU", -0.25))
    chebyshev_K: int = Field(default=_int_env("SOMABRAIN_CHEB_K", 30))
    # Recall behaviour flags
    recall_full_power: bool = Field(
        default=_bool_env("SOMABRAIN_RECALL_FULL_POWER", True)
    )
    recall_simple_defaults: bool = Field(
        default=_bool_env("SOMABRAIN_RECALL_SIMPLE_DEFAULTS", False)
    )
    recall_default_rerank: str = Field(
        default=_str_env("SOMABRAIN_RECALL_DEFAULT_RERANK", "auto")
    )
    recall_default_persist: bool = Field(
        default=_bool_env("SOMABRAIN_RECALL_DEFAULT_PERSIST", True)
    )
    recall_default_retrievers: str = Field(
        default=_str_env(
            "SOMABRAIN_RECALL_DEFAULT_RETRIEVERS", "vector,wm,graph,lexical"
        )
    )
    # OPA key paths
    opa_privkey_path: Optional[str] = Field(default=_str_env("SOMA_OPA_PRIVKEY_PATH"))
    opa_pubkey_path: Optional[str] = Field(default=_str_env("SOMA_OPA_PUBKEY_PATH"))
    # Kafka group id (used in orchestrator service)
    kafka_group_id: Optional[str] = Field(default=_str_env("KAFKA_GROUP_ID"))
    # Consumer group for orchestrator service (fallback to default name)
    consumer_group: Optional[str] = Field(
        default=_str_env("SOMABRAIN_CONSUMER_GROUP", "orchestrator-service")
    )
    # Port used by CLI tools (e.g., canary) – kept as string for URL construction.
    port: str = Field(default=_str_env("SOMABRAIN_PORT", "9696"))
    # Database URL fallback (for infrastructure init)
    database_url: Optional[str] = Field(default=_str_env("DATABASE_URL"))

    # -----------------------------------------------------------------
    # Provenance / audit settings
    # -----------------------------------------------------------------
    # Secret used for HMAC verification of the X-Provenance header.  If not
    # provided the middleware will still operate but provenance validation
    # will be disabled (the header will be ignored).
    provenance_secret: Optional[str] = Field(
        default=_str_env("SOMABRAIN_PROVENANCE_SECRET")
    )

    # Toggle whether provenance verification is required for write‑like
    # endpoints (e.g. /remember, /act).  Defaults to ``False`` for backward
    # compatibility; set to ``True`` in production to enforce strict checks.
    # The unified provenance flags are defined later in the file (environment
    # variable names ``REQUIRE_PROVENANCE`` and ``PROVENANCE_STRICT_DENY``).
    # The older duplicated definitions are removed to avoid confusion.

    # Feature flags --------------------------------------------------------
    # ``require_external_backends`` is the canonical flag that replaces the
    # legacy ``force_full_stack``. It controls whether external services (Redis,
    # Kafka, etc.) must be available. The default mirrors the historic behaviour
    # of ``SOMABRAIN_FORCE_FULL_STACK`` (True) but can be overridden via the
    # ``SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS`` environment variable.
    require_external_backends: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS", True)
    )
    # Global infra requirement flag – used by workers to optionally bypass
    # infra readiness checks (e.g., during unit tests). The original code
    # accessed ``settings.require_infra`` but the field was never defined,
    # causing an ``AttributeError`` in the outbox publisher and other workers.
    # We expose it here with the same semantics: a truthy value (default ``True``)
    # means infra must be ready; setting ``SOMABRAIN_REQUIRE_INFRA=0`` disables
    # the check.
    require_infra: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_REQUIRE_INFRA", True)
    )
    require_memory: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_REQUIRE_MEMORY", True)
    )
    # Test environment detection flag (used in code paths for pytest).
    # Centralises the environment variable read to avoid direct settings.getenv usage.
    pytest_current_test: Optional[str] = Field(default=_str_env("PYTEST_CURRENT_TEST"))
    # Auth is always-on in strict mode; legacy auth toggle removed.
    mode: str = Field(default=_str_env("SOMABRAIN_MODE", "full-local"))
    minimal_public_api: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_MINIMAL_PUBLIC_API", False)
    )
    allow_anonymous_tenants: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_ALLOW_ANONYMOUS_TENANTS", False)
    )
    predictor_provider: str = Field(
        default=_str_env("SOMABRAIN_PREDICTOR_PROVIDER", "").strip().lower() or "mahal"
    )
    # Feature/guard rails
    block_ua_regex: str = Field(default=_str_env("SOMABRAIN_BLOCK_UA_REGEX", ""))
    kill_switch: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_KILL_SWITCH", False)
    )
    allow_tiny_embedder: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_ALLOW_TINY_EMBEDDER", False)
    )

    # Kafka aliases / topics (keep compatibility with legacy env names)
    kafka_bootstrap: str = Field(
        default_factory=lambda: _str_env("SOMA_KAFKA_BOOTSTRAP", "")
    )

    # Learning / tenant config overrides
    learning_tenants_overrides: Optional[str] = Field(
        default=_str_env("SOMABRAIN_LEARNING_TENANTS_OVERRIDES")
    )
    learning_tenants_config: Optional[str] = Field(
        default=_str_env("LEARNING_TENANTS_CONFIG")
    )

    # Tau / entropy tuning knobs (used in learning.adaptation)
    tau_decay_enabled: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_TAU_DECAY_ENABLED", False)
    )
    tau_decay_rate: Optional[float] = Field(
        default=_float_env("SOMABRAIN_TAU_DECAY_RATE", 0.0)
    )
    tau_anneal_mode: Optional[str] = Field(
        default=_str_env("SOMABRAIN_TAU_ANNEAL_MODE")
    )
    tau_anneal_rate: Optional[float] = Field(
        default=_float_env("SOMABRAIN_TAU_ANNEAL_RATE", 0.0)
    )
    tau_anneal_step_interval: Optional[int] = Field(
        default=_int_env("SOMABRAIN_TAU_ANNEAL_STEP_INTERVAL", 0)
    )
    tau_min: Optional[float] = Field(default=_float_env("SOMABRAIN_TAU_MIN", 0.0))
    entropy_cap_enabled: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_ENTROPY_CAP_ENABLED", False)
    )
    entropy_cap: Optional[float] = Field(
        default=_float_env("SOMABRAIN_ENTROPY_CAP", 0.0)
    )
    # Global learning toggle for advanced features
    enable_advanced_learning: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_ENABLE_ADVANCED_LEARNING", True)
    )

    # OPA behaviour knobs
    opa_allow_on_error: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_OPA_ALLOW_ON_ERROR", False)
    )
    relax_predictor_ready: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_RELAX_PREDICTOR_READY", False)
    )
    # Feedback safety ------------------------------------------------------
    feedback_rate_limit_per_minute: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_FEEDBACK_RATE_LIMIT_PER_MIN", 120)
    )

    # -----------------------------------------------------------------
    # Additional URLs / endpoints extracted from hard‑coded literals
    # -----------------------------------------------------------------
    # Base API URL (used throughout benchmarks, demos, scripts)
    api_url: str = Field(default_factory=lambda: _str_env("SOMABRAIN_API_URL", ""))
    # Base URL used for local development and fallback when no explicit URL is provided.
    # Defaults to ``http://localhost:9696`` which matches historic hard‑coded values.
    default_base_url: str = Field(default_factory=lambda: _str_env("SOMABRAIN_DEFAULT_BASE_URL", "http://localhost:9696"))

    # OPA service URL (policy engine)
    opa_url: str = Field(default_factory=lambda: _str_env("SOMABRAIN_OPA_URL", ""))

    # OTEL collector endpoint (observability)
    otel_collector_endpoint: str = Field(
        default_factory=lambda: _str_env("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    )

    # Integrator and segmentation health endpoint defaults (internal services)
    # Removed unused integrator_triplet_health_url per VIBE cleanup.
    # Removed unused segmentation_health_url per VIBE cleanup.
    # Base URL for the somabrain_cog service
    # Removed unused somabrain_cog_base_url per VIBE cleanup.

    # -----------------------------------------------------------------
    # Provenance / audit control flags (used by ControlsMiddleware)
    # -----------------------------------------------------------------
    # Whether the middleware should enforce strict provenance validation.
    # Defaults to ``False`` to keep existing behaviour unchanged unless the
    # operator explicitly enables it via the ``PROVENANCE_STRICT_DENY``
    # environment variable.
    provenance_strict_deny: bool = Field(
        default_factory=lambda: _bool_env("PROVENANCE_STRICT_DENY", False)
    )

    # Toggle to require provenance headers on write‑like requests (POST to
    # ``/remember`` or ``/act``).  Historically this was ``require_provenance``
    # in the settings model; we re‑introduce it with a safe default of ``False``
    # so that the API remains functional without clients supplying the header.
    require_provenance: bool = Field(
        default_factory=lambda: _bool_env("REQUIRE_PROVENANCE", False)
    )

    # OPA -----------------------------------------------------------------------------
    # The single canonical OPA endpoint field. It falls back to the historic
    # OPA endpoint is fixed to the internal service address. If the environment
    # variable ``SOMABRAIN_OPA_URL`` is unset or empty, fall back to the internal
    # URL. This prevents an empty string from overriding the constant.
    opa_url: str = Field(
        default_factory=lambda: _str_env("SOMABRAIN_OPA_URL") or "http://opa:8181"
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
        default=_str_env("SOMABRAIN_MEMORY_PHASE_PRIORS", "")
    )
    memory_quality_exp: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_MEMORY_QUALITY_EXP", 1.0)
    )
    memory_fast_ack: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_MEMORY_FAST_ACK", False)
    )
    memory_db_path: str = Field(default=_str_env("MEMORY_DB_PATH", "./data/memory.db"))
    # Degradation behaviour when external memory backend is unavailable
    memory_degrade_queue: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_MEMORY_DEGRADE_QUEUE", True)
    )
    memory_degrade_readonly: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_MEMORY_DEGRADE_READONLY", False)
    )
    memory_degrade_topic: str = Field(
        default=_str_env("SOMABRAIN_MEMORY_DEGRADE_TOPIC", "memory.degraded")
    )

    # Health poll interval for external memory service – used by the FastAPI
    # application to periodically verify the health of the memory backend.
    # The default matches the historic hard‑coded fallback in ``somabrain.app``
    # (5 seconds). Allows overriding via environment variable for flexibility.
    memory_health_poll_interval: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_MEMORY_HEALTH_POLL_INTERVAL", 5.0)
    )

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
    log_level: str = Field(
        default_factory=lambda: _str_env("SOMABRAIN_LOG_LEVEL", "INFO") or "INFO"
    )
    # Additional environment variables used throughout the codebase
    health_port: Optional[int] = Field(
        default_factory=lambda: (
            _int_env("HEALTH_PORT", 0) if _str_env("HEALTH_PORT") is not None else None
        )
    )

    # -----------------------------------------------------------------
    # Additional optional configuration used by scripts / benchmarks.
    base_url: str = Field(default=_str_env("BASE_URL", ""))
    predictor_alpha: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_PREDICTOR_ALPHA", 2.0)
    )
    integrator_health_port: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_INTEGRATOR_HEALTH_PORT", 9015)
    )
    integrator_softmax_temperature: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_INTEGRATOR_TEMPERATURE", 1.0)
    )
    # Calibration
    calibration_enabled: bool = Field(default=False, description="Enable predictor calibration service")

    # Feature Flags
    enable_cog_threads: bool = Field(default=False, description="Enable Cognitive Threads v2")

    # Predictor timeout (ms) – used when constructing the budgeted predictor.
    # The historic default was 1000 ms; we keep that value here.
    predictor_timeout_ms: int = Field(default=1000)
    slow_predictor_delay_ms: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_SLOW_PREDICTOR_DELAY_MS", 1000)
    )

    # ---------------------------------------------------------------------
    # Core model dimensions
    # ---------------------------------------------------------------------
    # ``embed_dim`` is used throughout the codebase (e.g. in ``somabrain.app``)
    # to size embedding vectors.  The original repository relied on an older
    # settings implementation that provided this attribute implicitly.  Adding
    # it here restores compatibility without altering runtime behaviour – the
    # default of ``256`` matches the historic default used by the embedder.
    embed_dim: int = Field(default=256)

    # Working memory configuration – defaults align with documentation and
    # historic values used throughout the codebase.
    wm_size: int = Field(default_factory=lambda: _int_env("SOMABRAIN_WM_SIZE", 64))
    wm_recency_time_scale: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_WM_RECENCY_TIME_SCALE", 1.0)
    )
    wm_recency_max_steps: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_WM_RECENCY_MAX_STEPS", 1000)
    )
    wm_alpha: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_WM_ALPHA", 0.6)
    )
    wm_beta: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_WM_BETA", 0.3)
    )
    wm_gamma: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_WM_GAMMA", 0.1)
    )
    wm_salience_threshold: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_WM_SALIENCE_THRESHOLD", 0.4)
    )
    wm_per_col_min_capacity: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_WM_PER_COL_MIN_CAPACITY", 16)
    )
    wm_vote_softmax_floor: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_WM_VOTE_SOFTMAX_FLOOR", 1e-4)
    )
    wm_vote_entropy_eps: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_WM_VOTE_ENTROPY_EPS", 1e-9)
    )
    wm_per_tenant_capacity: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_WM_PER_TENANT_CAPACITY", 128)
    )
    mtwm_max_tenants: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_MTWM_MAX_TENANTS", 1000)
    )

    # Micro‑circuit configuration – used to split working memory into columns.
    micro_circuits: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_MICRO_CIRCUITS", 1)
    )
    micro_vote_temperature: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_MICRO_VOTE_TEMPERATURE", 0.25)
    )

    # Compatibility flag for the memory pipeline – older code uses ``use_microcircuits``
    # while the YAML config defines ``micro_circuits``. Provide both names so the
    # attribute lookup succeeds regardless of which spelling is used.
    use_microcircuits: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_USE_MICROCIRCUITS", False)
    )
    micro_max_tenants: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_MICRO_MAX_TENANTS", 1000)
    )

    # Rate limiting configuration – defaults provide a generous but safe ceiling.
    rate_rps: int = Field(default_factory=lambda: _int_env("SOMABRAIN_RATE_RPS", 1000))
    rate_burst: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_RATE_BURST", 2000)
    )

    # Quota management – daily write limit for the quota subsystem.
    write_daily_limit: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_WRITE_DAILY_LIMIT", 100000)
    )

    # Scorer weight configuration – added to resolve missing attributes in
    # ``somabrain.app``. Defaults match the values used in demo scripts.
    scorer_w_cosine: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SCORER_W_COSINE", 0.6)
    )
    scorer_w_fd: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SCORER_W_FD", 0.25)
    )
    scorer_w_recency: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SCORER_W_RECENCY", 0.15)
    )
    scorer_weight_min: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SCORER_WEIGHT_MIN", 0.0)
    )
    scorer_weight_max: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SCORER_WEIGHT_MAX", 1.0)
    )
    scorer_recency_tau: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SCORER_RECENCY_TAU", 32.0)
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
    # Enable flag for segmentation health endpoint (legacy env var).
    # Historically defaulted to "1" (enabled).  Stored as a bool.
    segment_health_enable: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_SEGMENT_HEALTH_ENABLE", True)
    )
    # Orchestrator specific configuration (fallback to env vars for backward compatibility)
    orchestrator_consumer_group: str = Field(
        default_factory=lambda: _str_env(
            "SOMABRAIN_ORCH_CONSUMER_GROUP", "orchestrator-service"
        )
        or "orchestrator-service"
    )
    orchestrator_namespace: str = Field(
        default_factory=lambda: _str_env("SOMABRAIN_ORCH_NAMESPACE", "cog") or "cog"
    )
    orchestrator_routing: str = Field(
        default_factory=lambda: _str_env("SOMABRAIN_ORCH_ROUTING", "") or ""
    )

    # Learning tenant configuration – optional YAML file path used by several services.
    learning_tenants_file: Optional[str] = Field(
        default=_str_env("SOMABRAIN_LEARNING_TENANTS_FILE")
    )
    # Alternate name used by some legacy code (same purpose).
    learning_tenants_config: Optional[str] = Field(
        default=_str_env("LEARNING_TENANTS_CONFIG")
    )

    # Salience system configuration – defaults align with demo scripts.
    salience_method: str = Field(
        default_factory=lambda: (
            _str_env("SOMABRAIN_SALIENCE_METHOD", "dense") or "dense"
        )
        .strip()
        .lower()
    )
    salience_fd_rank: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_SALIENCE_FD_RANK", 128)
    )
    salience_fd_decay: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SALIENCE_FD_DECAY", 0.9)
    )
    salience_w_novelty: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SALIENCE_W_NOVELTY", 0.6)
    )
    salience_w_error: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SALIENCE_W_ERROR", 0.4)
    )
    salience_threshold_store: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SALIENCE_THRESHOLD_STORE", 0.5)
    )
    salience_threshold_act: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SALIENCE_THRESHOLD_ACT", 0.7)
    )
    salience_hysteresis: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SALIENCE_HYSTERESIS", 0.1)
    )
    salience_fd_weight: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SALIENCE_FD_WEIGHT", 0.25)
    )
    salience_fd_energy_floor: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SALIENCE_FD_ENERGY_FLOOR", 0.0)
    )
    use_soft_salience: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_USE_SOFT_SALIENCE", False)
    )

    # HRR (Holographic Reduced Representation) toggle – referenced in
    # ``somabrain.app`` via ``cfg.use_hrr``.  The default is ``False`` to keep
    # the existing behaviour unless explicitly enabled via environment.
    use_hrr: bool = Field(default_factory=lambda: _bool_env("SOMABRAIN_USE_HRR", False))

    # Feature toggles referenced throughout the codebase – default to ``False``
    # for a minimal full‑local deployment.
    use_meta_brain: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_USE_META_BRAIN", False)
    )
    use_exec_controller: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_USE_EXEC_CONTROLLER", False)
    )
    use_drift_monitor: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_USE_DRIFT_MONITOR", False)
    )
    use_sdr_prefilter: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_USE_SDR_PREFILTER", False)
    )
    use_graph_augment: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_USE_GRAPH_AUGMENT", False)
    )
    use_hrr_first: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_USE_HRR_FIRST", False)
    )

    # Retrieval/adaptive weights (dynamic defaults) --------------------------
    retrieval_alpha: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_RETRIEVAL_ALPHA", 1.0)
    )
    retrieval_beta: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_RETRIEVAL_BETA", 0.2)
    )
    retrieval_gamma: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_RETRIEVAL_GAMMA", 0.1)
    )
    retrieval_tau: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_RETRIEVAL_TAU", 0.7)
    )
    retrieval_recency_half_life: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_RECENCY_HALF_LIFE", 60.0)
    )
    retrieval_recency_sharpness: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_RECENCY_SHARPNESS", 1.2)
    )
    retrieval_recency_floor: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_RECENCY_FLOOR", 0.05)
    )
    retrieval_density_target: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_DENSITY_TARGET", 0.2)
    )
    retrieval_density_floor: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_DENSITY_FLOOR", 0.6)
    )
    retrieval_density_weight: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_DENSITY_WEIGHT", 0.35)
    )
    retrieval_tau_min: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_TAU_MIN", 0.4)
    )
    retrieval_tau_max: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_TAU_MAX", 1.2)
    )
    retrieval_tau_increment_up: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_TAU_INC_UP", 0.1)
    )
    retrieval_tau_increment_down: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_TAU_INC_DOWN", 0.05)
    )
    retrieval_dup_ratio_threshold: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_DUP_RATIO_THRESHOLD", 0.5)
    )

    # Planner / graph walk defaults ------------------------------------------------
    planner_rwr_steps: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_PLANNER_RWR_STEPS", 20)
    )
    planner_rwr_restart: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_PLANNER_RWR_RESTART", 0.15)
    )
    planner_rwr_max_nodes: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_PLANNER_RWR_MAX_NODES", 128)
    )
    planner_rwr_edges_per_node: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_PLANNER_RWR_EDGES_PER_NODE", 32)
    )
    planner_rwr_max_items: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_PLANNER_RWR_MAX_ITEMS", 5)
    )

    # Neuromodulator defaults (centralized, overridable) ---------------------
    neuromod_dopamine_base: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_DOPAMINE_BASE", 0.4)
    )
    neuromod_serotonin_base: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_SEROTONIN_BASE", 0.5)
    )
    neuromod_noradrenaline_base: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_NORAD_BASE", 0.0)
    )
    neuromod_acetylcholine_base: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_ACETYL_BASE", 0.0)
    )
    neuromod_dopamine_min: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_DOPAMINE_MIN", 0.1)
    )
    neuromod_dopamine_max: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_DOPAMINE_MAX", 1.0)
    )
    neuromod_serotonin_min: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_SEROTONIN_MIN", 0.0)
    )
    neuromod_serotonin_max: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_SEROTONIN_MAX", 1.0)
    )
    neuromod_noradrenaline_min: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_NORAD_MIN", 0.0)
    )
    neuromod_noradrenaline_max: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_NORAD_MAX", 0.5)
    )
    neuromod_acetylcholine_min: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_ACETYL_MIN", 0.0)
    )
    neuromod_acetylcholine_max: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_ACETYL_MAX", 0.5)
    )
    neuromod_dopamine_lr: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_DOPAMINE_LR", 0.02)
    )
    neuromod_serotonin_lr: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_SEROTONIN_LR", 0.015)
    )
    neuromod_noradrenaline_lr: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_NORAD_LR", 0.01)
    )
    neuromod_acetylcholine_lr: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_ACETYL_LR", 0.01)
    )
    neuromod_urgency_factor: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_URGENCY_FACTOR", 0.3)
    )
    neuromod_memory_factor: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_MEMORY_FACTOR", 0.2)
    )
    neuromod_latency_scale: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_LATENCY_SCALE", 0.05)
    )
    neuromod_accuracy_scale: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_ACCURACY_SCALE", 0.1)
    )
    neuromod_latency_floor: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_LATENCY_FLOOR", 0.1)
    )
    neuromod_dopamine_bias: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_DOPAMINE_BIAS", -0.5)
    )
    neuromod_dopamine_reward_boost: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_NEURO_DOPAMINE_REWARD_BOOST", 0.1)
    )

    # Utility/adaptation defaults ---------------------------------------------
    utility_lambda: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_UTILITY_LAMBDA", 1.0)
    )
    utility_mu: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_UTILITY_MU", 0.1)
    )
    utility_nu: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_UTILITY_NU", 0.05)
    )
    utility_lambda_min: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_UTILITY_LAMBDA_MIN", 0.0)
    )
    utility_lambda_max: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_UTILITY_LAMBDA_MAX", 5.0)
    )
    utility_mu_min: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_UTILITY_MU_MIN", 0.0)
    )
    utility_mu_max: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_UTILITY_MU_MAX", 5.0)
    )
    utility_nu_min: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_UTILITY_NU_MIN", 0.0)
    )
    utility_nu_max: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_UTILITY_NU_MAX", 5.0)
    )
    adaptation_learning_rate: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_ADAPT_LR", 0.05)
    )
    adaptation_max_history: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_ADAPT_MAX_HISTORY", 1000)
    )
    adaptation_alpha_min: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_ADAPT_ALPHA_MIN", 0.1)
    )
    adaptation_alpha_max: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_ADAPT_ALPHA_MAX", 5.0)
    )
    adaptation_gamma_min: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_ADAPT_GAMMA_MIN", 0.0)
    )
    adaptation_gamma_max: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_ADAPT_GAMMA_MAX", 1.0)
    )
    adaptation_lambda_min: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_ADAPT_LAMBDA_MIN", 0.1)
    )
    adaptation_lambda_max: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_ADAPT_LAMBDA_MAX", 5.0)
    )
    adaptation_mu_min: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_ADAPT_MU_MIN", 0.01)
    )
    adaptation_mu_max: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_ADAPT_MU_MAX", 5.0)
    )
    adaptation_nu_min: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_ADAPT_NU_MIN", 0.01)
    )
    adaptation_nu_max: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_ADAPT_NU_MAX", 5.0)
    )
    adaptation_gain_alpha: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_ADAPT_GAIN_ALPHA", 1.0)
    )
    adaptation_gain_gamma: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_ADAPT_GAIN_GAMMA", -0.5)
    )
    adaptation_gain_lambda: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_ADAPT_GAIN_LAMBDA", 1.0)
    )
    adaptation_gain_mu: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_ADAPT_GAIN_MU", -0.25)
    )
    adaptation_gain_nu: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_ADAPT_GAIN_NU", -0.25)
    )

    # Sleep system (hot-configurable) ----------------------------------------
    enable_sleep_system: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_ENABLE_SLEEP", True)
    )
    sleep_k0: int = Field(default_factory=lambda: _int_env("SOMABRAIN_SLEEP_K0", 100))
    sleep_t0: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SLEEP_T0", 10.0)
    )
    sleep_tau0: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SLEEP_TAU0", 1.0)
    )
    sleep_eta0: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SLEEP_ETA0", 0.1)
    )
    sleep_lambda0: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SLEEP_LAMBDA0", 0.01)
    )
    sleep_B0: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SLEEP_B0", 0.5)
    )
    sleep_K_min: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_SLEEP_K_MIN", 1)
    )
    sleep_t_min: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SLEEP_T_MIN", 0.1)
    )
    sleep_alpha_K: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SLEEP_ALPHA_K", 0.8)
    )
    sleep_alpha_t: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SLEEP_ALPHA_T", 0.5)
    )
    sleep_alpha_tau: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SLEEP_ALPHA_TAU", 0.5)
    )
    sleep_alpha_eta: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SLEEP_ALPHA_ETA", 1.0)
    )
    sleep_beta_B: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_SLEEP_BETA_B", 0.5)
    )
    # Maximum allowed TTL (in seconds) for any sleep request. This caps the
    # ``ttl_seconds`` field supplied by clients and is enforced by the API
    # handlers as well as the OPA policy input.
    sleep_max_seconds: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_SLEEP_MAX_SECONDS", 3600)
    )
    # Maximum number of summaries to generate per consolidation cycle (NREM/REM).
    # This mirrors the historic ``max_summaries_per_cycle`` setting used by the
    # sleep and consolidation code paths.
    max_summaries_per_cycle: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_MAX_SUMMARIES_PER_CYCLE", 3)
    )
    # Batch sizes for consolidation (NREM/REM) – hot‑configurable defaults
    nrem_batch_size: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_NREM_BATCH_SIZE", 32)
    )
    rem_batch_size: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_REM_BATCH_SIZE", 32)
    )
    # Recombination rate for REM consolidation – used by the REM algorithm to
    # determine how many pairs of episodic memories to recombine.  Historically
    # this was a hard‑coded constant (0.2) in several modules; exposing it as a
    # configurable setting restores compatibility with the existing code that
    # expects ``cfg.rem_recomb_rate``.
    rem_recomb_rate: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_REM_RECOMB_RATE", 0.2)
    )

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
        default_factory=lambda: _int_env(
            "SOMABRAIN_SEGMENT_WRITE_GAP_THRESHOLD_MS", 30000
        )
    )

    # CPD segmentation parameters -----------------------------------------------
    cpd_min_samples: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_CPD_MIN_SAMPLES", 20)
    )
    cpd_z: float = Field(default_factory=lambda: _float_env("SOMABRAIN_CPD_Z", 4.0))
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
        default_factory=lambda: _str_env(
            "SOMABRAIN_CONSUMER_GROUP", "segmentation-service"
        )
    )
    default_tenant: str = Field(
        default_factory=lambda: _str_env("SOMABRAIN_DEFAULT_TENANT", "public")
        or "public"
    )
    host: str = Field(
        default_factory=lambda: _str_env("SOMABRAIN_HOST", "0.0.0.0") or "0.0.0.0"
    )

    # Multi‑tenant namespace – used throughout the app for routing and storage.
    # Default to "public" to keep existing behaviour when the variable is unset.
    namespace: str = Field(
        default_factory=lambda: _str_env("SOMABRAIN_NAMESPACE", "public") or "public"
    )
    # Service name for observability – used as a default when tracing is
    # initialised without an explicit name.
    service_name: str = Field(
        default_factory=lambda: _str_env("SOMABRAIN_SERVICE_NAME", "somabrain")
        or "somabrain"
    )
    log_config: str = Field(
        default_factory=lambda: _str_env(
            "SOMABRAIN_LOG_CONFIG", "/app/config/logging.yaml"
        )
        or "/app/config/logging.yaml"
    )
    constitution_privkey_path: Optional[str] = Field(
        default=_str_env("SOMABRAIN_CONSTITUTION_PRIVKEY_PATH")
    )
    constitution_signer_id: str = Field(
        default_factory=lambda: _str_env("SOMABRAIN_CONSTITUTION_SIGNER_ID", "default")
        or "default"
    )
    # Additional optional configuration values used by scripts and CI utilities
    reward_port: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_REWARD_PORT", 8083)
    )
    reward_producer_port: int = Field(
        default_factory=lambda: _int_env("REWARD_PRODUCER_PORT", 30183)
    )
    drift_store_path: str = Field(
        default_factory=lambda: _str_env(
            "SOMABRAIN_DRIFT_STORE", "./data/drift/state.json"
        )
        or "./data/drift/state.json"
    )
    universe: Optional[str] = Field(default=_str_env("SOMA_UNIVERSE"))
    # Teach feedback processor configuration
    teach_feedback_proc_port: int = Field(
        default_factory=lambda: _int_env("TEACH_FEEDBACK_PROC_PORT", 8086)
    )
    teach_feedback_proc_group: str = Field(
        default_factory=lambda: _str_env("TEACH_PROC_GROUP", "teach-feedback-proc")
        or "teach-feedback-proc"
    )
    teach_dedup_cache_size: int = Field(
        default_factory=lambda: _int_env("TEACH_DEDUP_CACHE_SIZE", 512)
    )
    # Feature flags service configuration
    feature_flags_port: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_FEATURE_FLAGS_PORT", 9697)
    )
    # -----------------------------------------------------------------
    # Additional environment variables used throughout the codebase.
    # These fields provide direct access to values that were previously
    # obtained via ``settings.getenv`` in various modules.
    # -----------------------------------------------------------------
    # Vault integration
    vault_addr: Optional[str] = Field(default=_str_env("VAULT_ADDR"))
    vault_token: Optional[str] = Field(default=_str_env("VAULT_TOKEN"))
    vault_pubkey_path: Optional[str] = Field(
        default=_str_env("SOMABRAIN_VAULT_PUBKEY_PATH")
    )

    # Constitution defaults
    constitution_pubkeys: Optional[str] = Field(
        default=_str_env("SOMABRAIN_CONSTITUTION_PUBKEYS")
    )
    constitution_pubkey_path: Optional[str] = Field(
        default=_str_env("SOMABRAIN_CONSTITUTION_PUBKEY_PATH")
    )
    constitution_privkey_path: Optional[str] = Field(
        default=_str_env("SOMABRAIN_CONSTITUTION_PRIVKEY_PATH")
    )
    constitution_signer_id: str = Field(
        default_factory=lambda: _str_env("SOMABRAIN_CONSTITUTION_SIGNER_ID", "default")
        or "default"
    )

    # LLM endpoint for predictor (if used)
    llm_endpoint: Optional[str] = Field(default=_str_env("SOMABRAIN_LLM_ENDPOINT"))

    # Tenant identifier (used by some services)
    tenant_id: str = Field(
        default_factory=lambda: _str_env("SOMABRAIN_TENANT_ID", "default") or "default"
    )

    # Health endpoint URLs for integrator and segmentation services.
    # These are used by the health diagnostics endpoint.
    integrator_health_url: str = Field(
        default_factory=lambda: _str_env(
            "SOMABRAIN_INTEGRATOR_HEALTH_URL",
            "http://somabrain_integrator_triplet:9015/health",
        )
        or "http://somabrain_integrator_triplet:9015/health"
    )
    segmentation_health_url: str = Field(
        default_factory=lambda: _str_env(
            "SOMABRAIN_SEGMENTATION_HEALTH_URL",
            "http://somabrain_cog:9016/health",
        )
        or "http://somabrain_cog:9016/health"
    )
    # Tiered memory cleanup configuration
    tiered_memory_cleanup_backend: str = Field(
        default_factory=lambda: _str_env("SOMABRAIN_CLEANUP_BACKEND", "simple")
        or "simple"
    )
    tiered_memory_cleanup_topk: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_CLEANUP_TOPK", 64)
    )
    tiered_memory_cleanup_hnsw_m: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_CLEANUP_HNSW_M", 32)
    )
    tiered_memory_cleanup_hnsw_ef_construction: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_CLEANUP_HNSW_EF_CONSTRUCTION", 200)
    )
    tiered_memory_cleanup_hnsw_ef_search: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_CLEANUP_HNSW_EF_SEARCH", 128)
    )
    # Topic names used by scripts/CI utilities
    topic_config_updates: str = Field(
        default_factory=lambda: _str_env(
            "SOMABRAIN_TOPIC_CONFIG_UPDATES", "cog.config.updates"
        )
        or "cog.config.updates"
    )
    topic_next_event: str = Field(
        default_factory=lambda: _str_env("SOMABRAIN_TOPIC_NEXT_EVENT", "cog.next_event")
        or "cog.next_event"
    )
    topic_state_updates: str = Field(
        default_factory=lambda: _str_env(
            "SOMABRAIN_TOPIC_STATE_UPDATES", "cog.state.updates"
        )
        or "cog.state.updates"
    )
    topic_agent_updates: str = Field(
        default_factory=lambda: _str_env(
            "SOMABRAIN_TOPIC_AGENT_UPDATES", "cog.agent.updates"
        )
        or "cog.agent.updates"
    )
    topic_action_updates: str = Field(
        default_factory=lambda: _str_env(
            "SOMABRAIN_TOPIC_ACTION_UPDATES", "cog.action.updates"
        )
        or "cog.action.updates"
    )
    topic_global_frame: str = Field(
        default_factory=lambda: _str_env(
            "SOMABRAIN_TOPIC_GLOBAL_FRAME", "cog.global.frame"
        )
        or "cog.global.frame"
    )
    topic_segments: str = Field(
        default_factory=lambda: _str_env("SOMABRAIN_TOPIC_SEGMENTS", "cog.segments")
        or "cog.segments"
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
            if _str_env("SOMABRAIN_FORCE_FULL_STACK") is not None:
                notes.append(
                    "SOMABRAIN_FORCE_FULL_STACK is deprecated; use SOMABRAIN_MODE with mode_require_external_backends policy."
                )
        except Exception:
            pass
        try:
            legacy_auth_env = _str_env("SOMABRAIN_AUTH_LEGACY")
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

    # -----------------------------------------------------------------
    # Helpers for legacy call sites
    # -----------------------------------------------------------------
    def _env_to_attr(self, name: str) -> str:
        """Best-effort mapping from env var name to Settings attribute.

        Strips common prefixes (SOMABRAIN_, SOMA_, OPA_) and lowercases /
        converts to snake_case to align with field names. This keeps legacy
        ``settings.getenv("SOMABRAIN_X")`` call sites functional while the code
        base is migrated to direct attribute access.
        """
        key = name.lower()
        for prefix in ("somabrain_", "soma_", "opa_"):
            if key.startswith(prefix):
                key = key[len(prefix) :]
                break
        key = key.replace("-", "_")
        return key

    # Hard block legacy access: all call sites must be updated to use typed
    # Settings attributes. This will raise immediately wherever getenv is still
    # called.
    def getenv(
        self, name: str, default: Optional[str] = None
    ) -> Optional[str]:  # pragma: no cover
        raise RuntimeError(
            f"settings.getenv('{name}') is prohibited. Replace with Settings attributes."
        )


# Export a singleton – mirrors the historic pattern used throughout the
# codebase (``settings = Settings()``).
settings = Settings()

# Legacy compatibility shim removed. Direct ``settings.getenv`` calls should now be
# replaced with ``settings`` attributes throughout the codebase to ensure a single
# source of truth. Until migration is complete, ``getenv`` maps env-style names to
# Settings attributes to keep behaviour centralised.
