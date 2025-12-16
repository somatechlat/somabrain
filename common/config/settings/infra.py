"""Infrastructure settings for SomaBrain.

This module contains configuration for external infrastructure services:
- Redis
- Kafka
- PostgreSQL
- Milvus
- OPA (Open Policy Agent)
- Circuit breaker settings
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from common.config.settings.base import (
    BaseSettings,
    Field,
    SettingsConfigDict,
    _bool_env,
    _float_env,
    _int_env,
    _str_env,
)


class InfraSettingsMixin(BaseSettings):
    """Infrastructure-related settings mixin."""

    # PostgreSQL
    postgres_dsn: str = Field(
        default_factory=lambda: _str_env("SOMABRAIN_POSTGRES_DSN", "")
    )
    database_url: Optional[str] = Field(default=_str_env("DATABASE_URL"))

    # Redis
    redis_url: str = Field(
        default_factory=lambda: _str_env("SOMABRAIN_REDIS_URL")
        or _str_env("REDIS_URL")
        or ""
    )
    redis_host: Optional[str] = Field(
        default=_str_env("SOMABRAIN_REDIS_HOST") or _str_env("REDIS_HOST")
    )
    redis_port: Optional[int] = Field(
        default=_int_env("SOMABRAIN_REDIS_PORT", _int_env("REDIS_PORT", 6379))
    )
    redis_db: Optional[int] = Field(
        default=_int_env("SOMABRAIN_REDIS_DB", _int_env("REDIS_DB", 0))
    )

    # Kafka
    kafka_bootstrap_servers: str = Field(
        default_factory=lambda: (
            _str_env("SOMABRAIN_KAFKA_URL") or _str_env("KAFKA_BOOTSTRAP_SERVERS") or ""
        ).replace("kafka://", "")
    )
    kafka_host: Optional[str] = Field(
        default=_str_env("SOMABRAIN_KAFKA_HOST") or _str_env("KAFKA_HOST")
    )
    kafka_port: Optional[int] = Field(
        default=_int_env("SOMABRAIN_KAFKA_PORT", _int_env("KAFKA_PORT", 0))
    )
    kafka_scheme: Optional[str] = Field(
        default=_str_env("SOMABRAIN_KAFKA_SCHEME") or _str_env("KAFKA_SCHEME") or "kafka"
    )
    kafka_url: str = Field(default_factory=lambda: _str_env("SOMABRAIN_KAFKA_URL", ""))
    kafka_bootstrap: str = Field(
        default_factory=lambda: _str_env("SOMA_KAFKA_BOOTSTRAP", "")
    )
    kafka_group_id: Optional[str] = Field(default=_str_env("KAFKA_GROUP_ID"))
    consumer_group: Optional[str] = Field(
        default=_str_env("SOMABRAIN_CONSUMER_GROUP", "orchestrator-service")
    )

    # Milvus
    milvus_host: Optional[str] = Field(
        default=_str_env("MILVUS_HOST") or _str_env("SOMABRAIN_MILVUS_HOST")
    )
    milvus_port: Optional[int] = Field(
        default=_int_env("MILVUS_PORT", _int_env("SOMABRAIN_MILVUS_PORT", 19530))
    )
    milvus_collection: str = Field(default=_str_env("MILVUS_COLLECTION", "oak_options"))
    milvus_segment_refresh_interval: float = Field(
        default=_float_env("MILVUS_SEGMENT_REFRESH_INTERVAL", 60.0)
    )
    milvus_latency_window: int = Field(default=_int_env("MILVUS_LATENCY_WINDOW", 50))
    milvus_url: Optional[str] = Field(
        default_factory=lambda: (
            f"{_str_env('MILVUS_HOST', 'localhost')}:{_int_env('MILVUS_PORT', 19530)}"
        )
    )

    # OPA
    opa_host: Optional[str] = Field(
        default=_str_env("SOMABRAIN_OPA_HOST") or _str_env("OPA_HOST")
    )
    opa_port: Optional[int] = Field(
        default=_int_env("SOMABRAIN_OPA_PORT", _int_env("OPA_PORT", 0))
    )
    opa_scheme: Optional[str] = Field(
        default=_str_env("SOMABRAIN_OPA_SCHEME") or _str_env("OPA_SCHEME") or "http"
    )
    opa_url: str = Field(
        default_factory=lambda: _str_env("SOMABRAIN_OPA_URL") or "http://opa:8181"
    )
    opa_timeout_seconds: float = Field(
        default_factory=lambda: _float_env("SOMA_OPA_TIMEOUT", 2.0)
    )
    opa_bundle_path: Optional[str] = Field(
        default=_str_env("OPA_BUNDLE_PATH") or "./opa"
    )
    opa_allow_on_error: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_OPA_ALLOW_ON_ERROR", False)
    )

    # Circuit breaker
    circuit_failure_threshold: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_CIRCUIT_FAILURE_THRESHOLD", 3)
    )
    circuit_reset_interval: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_CIRCUIT_RESET_INTERVAL", 60.0)
    )
    circuit_cooldown_interval: float = Field(
        default_factory=lambda: _float_env("SOMABRAIN_CIRCUIT_COOLDOWN_INTERVAL", 0.0)
    )

    # Feature flags for infrastructure
    require_external_backends: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS", True)
    )
    require_memory: bool = Field(default=True)
    require_infra: str = Field(default="1")
    running_in_docker: bool = Field(
        default_factory=lambda: _bool_env("RUNNING_IN_DOCKER", False)
    )

    # HTTP client settings
    http_max_connections: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_HTTP_MAX_CONNS", 64)
    )
    http_keepalive_connections: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_HTTP_KEEPALIVE", 32)
    )
    http_retries: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_HTTP_RETRIES", 1)
    )

    # Logging and metrics
    log_path: str = Field(
        default=_str_env("SOMABRAIN_LOG_PATH", "somabrain.log").strip()
    )
    log_level: str = Field(
        default_factory=lambda: _str_env("SOMABRAIN_LOG_LEVEL", "INFO") or "INFO"
    )
    metrics_sink: Optional[str] = Field(
        default=_str_env("SOMABRAIN_METRICS_SINK"),
        description="Path to write metrics snapshot (optional)",
    )
    log_config: str = Field(
        default_factory=lambda: _str_env(
            "SOMABRAIN_LOG_CONFIG", "/app/config/logging.yaml"
        )
        or "/app/config/logging.yaml"
    )

    # Service configuration
    home_dir: str = Field(default_factory=lambda: _str_env("HOME", "") or "")
    host: str = Field(
        default_factory=lambda: _str_env("SOMABRAIN_HOST", "0.0.0.0") or "0.0.0.0"
    )
    port: str = Field(default=_str_env("SOMABRAIN_PORT", "9696"))
    host_port: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_HOST_PORT", 9696)
    )
    workers: int = Field(default_factory=lambda: _int_env("SOMABRAIN_WORKERS", 1))
    service_name: str = Field(
        default_factory=lambda: _str_env("SOMABRAIN_SERVICE_NAME", "somabrain")
        or "somabrain"
    )
    namespace: str = Field(
        default_factory=lambda: _str_env("SOMABRAIN_NAMESPACE", "public") or "public"
    )
    default_tenant: str = Field(
        default_factory=lambda: _str_env("SOMABRAIN_DEFAULT_TENANT", "public")
        or "public"
    )
    tenant_id: str = Field(
        default_factory=lambda: _str_env("SOMABRAIN_TENANT_ID", "default") or "default"
    )

    # URLs
    api_url: str = Field(default_factory=lambda: _str_env("SOMABRAIN_API_URL", ""))
    default_base_url: str = Field(
        default_factory=lambda: _str_env(
            "SOMABRAIN_DEFAULT_BASE_URL", "http://localhost:9696"
        )
    )
    base_url: str = Field(default=_str_env("BASE_URL", ""))
    supervisor_url: Optional[str] = Field(default=_str_env("SUPERVISOR_URL"))
    supervisor_http_user: str = Field(default=_str_env("SUPERVISOR_HTTP_USER", "admin"))
    supervisor_http_pass: str = Field(default=_str_env("SUPERVISOR_HTTP_PASS", "soma"))
    integrator_url: Optional[str] = Field(default=_str_env("INTEGRATOR_URL"))
    segmentation_url: Optional[str] = Field(default=_str_env("SEGMENTATION_URL"))
    otel_collector_endpoint: str = Field(
        default_factory=lambda: _str_env("OTEL_EXPORTER_OTLP_ENDPOINT", "")
    )

    # Health endpoints
    health_port: Optional[int] = Field(
        default_factory=lambda: (
            _int_env("HEALTH_PORT", 0) if _str_env("HEALTH_PORT") is not None else None
        )
    )
    integrator_health_port: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_INTEGRATOR_HEALTH_PORT", 9015)
    )
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

    # Kafka topics
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

    # Outbox configuration
    outbox_batch_size: int = Field(default=100)
    outbox_max_delay: float = Field(default=5.0)
    outbox_max_retries: int = Field(default=5)
    outbox_poll_interval: float = Field(default=1.0)
    outbox_producer_retry_ms: int = Field(default=1000)
    outbox_api_token: Optional[str] = Field(
        default=_str_env("SOMABRAIN_API_TOKEN") or _str_env("SOMA_API_TOKEN")
    )

    # Journal
    journal_dir: str = Field(
        default=_str_env("SOMABRAIN_JOURNAL_DIR", "/tmp/somabrain_journal")
    )
    journal_replay_interval: int = Field(default=300)
    journal_max_file_size: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_JOURNAL_MAX_FILE_SIZE", 104857600),
        description="Maximum journal file size in bytes (default 100MB)",
    )
    journal_max_files: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_JOURNAL_MAX_FILES", 10),
        description="Maximum number of journal files to retain",
    )
    journal_rotation_interval: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_JOURNAL_ROTATION_INTERVAL", 86400),
        description="Journal rotation interval in seconds (default 24 hours)",
    )
    journal_retention_days: int = Field(
        default_factory=lambda: _int_env("SOMABRAIN_JOURNAL_RETENTION_DAYS", 7),
        description="Number of days to retain journal files",
    )
    journal_compression: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_JOURNAL_COMPRESSION", True),
        description="Enable journal file compression",
    )
    journal_sync_writes: bool = Field(
        default_factory=lambda: _bool_env("SOMABRAIN_JOURNAL_SYNC_WRITES", True),
        description="Enable fsync for journal durability",
    )

    # Test environment
    pytest_current_test: Optional[str] = Field(default=_str_env("PYTEST_CURRENT_TEST"))
    TEST_MODE: bool = Field(default_factory=lambda: _bool_env("OAK_TEST_MODE", False))

    # Documentation build detection (for Sphinx)
    sphinx_build: bool = Field(
        default_factory=lambda: _bool_env("SPHINX_BUILD", False),
        description="Set to true when building documentation with Sphinx",
    )

    # CLI server settings (generic HOST/PORT for uvicorn)
    cli_host: str = Field(
        default_factory=lambda: _str_env("HOST", "0.0.0.0") or "0.0.0.0",
        description="Host for CLI server (uvicorn)",
    )
    cli_port: int = Field(
        default_factory=lambda: _int_env("PORT", 8000) or 8000,
        description="Port for CLI server (uvicorn)",
    )

    # Mode configuration
    mode: str = Field(default=_str_env("SOMABRAIN_MODE", "full-local"))

    # Pydantic configuration
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parents[3] / ".env"),
        case_sensitive=False,
        extra="allow",
    )
