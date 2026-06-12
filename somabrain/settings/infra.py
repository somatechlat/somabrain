"""Infrastructure settings and connection defaults for SomaBrain.

This module resolves service endpoints in three stages:
1. Optional Vault bootstrap writes secrets into the process environment.
2. Explicit environment variables win over every inferred default.
3. Remaining gaps are filled from Docker-aware local defaults.

That split lets the same code run in standalone Docker, CI, and direct local
development without scattering connection logic across the codebase.
"""

import os

import environ  # type: ignore[import-untyped]

env = environ.Env()

# ============================================================================
# INFRASTRUCTURE SETTINGS
# ============================================================================

# TensorFlow/Metal can trigger device-handling crashes on some macOS hosts.
# Pinning this before downstream imports keeps local diagnostics reproducible.
os.environ["TF_METAL_DEVICE_HANDLING"] = "1"


def _set_env_if_present(name: str, value: object | None) -> None:
    """Set an environment variable only when Vault returned a real value."""
    if value is None:
        return
    text = str(value).strip()
    if text:
        os.environ[name] = text


# Preload secrets from Vault when the process was bootstrapped with Vault
# coordinates. The rest of this module still supports plain environment-based
# configuration when Vault is intentionally absent.
try:
    from somabrain.core.security.vault_client import (
        SecretNotFound,
        VaultNotConfigured,
        get_db_credentials,
        get_runtime_secrets,
        get_secret,
    )

    try:
        db_creds = get_db_credentials()
        # Construct DSN from Vault if available
        # Expected format: postgres://user:pass@host:port/db
        if db_creds:
            _user = db_creds.get("username")
            _pass = db_creds.get("password")
            _host = db_creds.get("host", "127.0.0.1")
            _port = db_creds.get("port", 5432)
            _name = db_creds.get("dbname", "somabrain")

            # Vault wins over any stale DSN inherited from the shell.
            os.environ["SOMABRAIN_POSTGRES_DSN"] = (
                f"postgres://{_user}:{_pass}@{_host}:{_port}/{_name}"
            )

            # Redis from Vault?
            redis_creds = get_secret("somabrain/redis")
            if redis_creds:
                os.environ["SOMABRAIN_REDIS_URL"] = redis_creds.get("url", "")

            runtime_secrets = get_runtime_secrets()
            if runtime_secrets:
                _set_env_if_present(
                    "SOMABRAIN_MEMORY_HTTP_TOKEN",
                    runtime_secrets.get("memory_http_token"),
                )
                _set_env_if_present(
                    "SUPERVISOR_HTTP_PASS",
                    runtime_secrets.get("supervisor_http_pass"),
                )
                _set_env_if_present(
                    "OUTBOX_API_TOKEN",
                    runtime_secrets.get("api_token"),
                )
                _set_env_if_present(
                    "SOMABRAIN_API_TOKEN",
                    runtime_secrets.get("api_token"),
                )
                _set_env_if_present(
                    "SOMA_API_TOKEN",
                    runtime_secrets.get("api_token"),
                )

    except (SecretNotFound, VaultNotConfigured, ImportError):
        # Fallback to pure Env if Vault not configured (e.g. CI without Vault)
        pass
except ImportError:
    pass

SOMABRAIN_POSTGRES_DSN = env.str("SOMABRAIN_POSTGRES_DSN", default="")
# Remove legacy DATABASE_URL fallback to avoid collisions
# DATABASE_URL = env.str("DATABASE_URL", default=None)


# Kubernetes service injection can expose ports as tcp://host:port strings.
# Normalize those values before the rest of settings consumes them as integers.
def _parse_port(value: str | int | None, default: int) -> int:
    if not value:
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.startswith("tcp://"):
        try:
            return int(value.rsplit(":", 1)[-1])
        except (ValueError, IndexError):
            return default
    try:
        return int(value)
    except ValueError:
        return default


# Redis
SOMABRAIN_REDIS_URL = env.str("SOMABRAIN_REDIS_URL", default="")
SOMABRAIN_REDIS_HOST = env.str("SOMABRAIN_REDIS_HOST", default="127.0.0.1")
SOMABRAIN_REDIS_PORT = _parse_port(env.str("SOMABRAIN_REDIS_PORT", default=None), 6379)
SOMABRAIN_REDIS_DB = env.int("SOMABRAIN_REDIS_DB", default=0)

# Kafka
KAFKA_BOOTSTRAP_SERVERS = env.str(
    "KAFKA_BOOTSTRAP_SERVERS", default=env.str("SOMABRAIN_KAFKA_URL", default="")
).replace("kafka://", "")
SOMABRAIN_KAFKA_HOST = env.str(
    "SOMABRAIN_KAFKA_HOST", default=env.str("KAFKA_HOST", default=None)
)
SOMABRAIN_KAFKA_PORT = env.int(
    "SOMABRAIN_KAFKA_PORT", default=env.int("KAFKA_PORT", default=0)
)
SOMABRAIN_KAFKA_SCHEME = env.str(
    "SOMABRAIN_KAFKA_SCHEME", default=env.str("KAFKA_SCHEME", default="kafka")
)
SOMABRAIN_KAFKA_URL = env.str("SOMABRAIN_KAFKA_URL", default="")
SOMA_KAFKA_BOOTSTRAP = env.str("SOMA_KAFKA_BOOTSTRAP", default="")
KAFKA_GROUP_ID = env.str("KAFKA_GROUP_ID", default=None)
SOMABRAIN_CONSUMER_GROUP = env.str(
    "SOMABRAIN_CONSUMER_GROUP", default="orchestrator-service"
)

# Milvus
SOMABRAIN_MILVUS_HOST = env.str(
    "MILVUS_HOST", default=env.str("SOMABRAIN_MILVUS_HOST", default=None)
)
SOMABRAIN_MILVUS_PORT = env.int(
    "MILVUS_PORT", default=env.int("SOMABRAIN_MILVUS_PORT", default=19530)
)
SOMABRAIN_MILVUS_COLLECTION = env.str("MILVUS_COLLECTION", default="oak_options")
MILVUS_SEGMENT_REFRESH_INTERVAL = env.float(
    "MILVUS_SEGMENT_REFRESH_INTERVAL", default=60.0
)
MILVUS_LATENCY_WINDOW = env.int("MILVUS_LATENCY_WINDOW", default=50)

# OPA
SOMABRAIN_OPA_HOST = env.str(
    "SOMABRAIN_OPA_HOST", default=env.str("OPA_HOST", default=None)
)
SOMABRAIN_OPA_PORT = env.int(
    "SOMABRAIN_OPA_PORT", default=env.int("OPA_PORT", default=0)
)
SOMABRAIN_OPA_SCHEME = env.str(
    "SOMABRAIN_OPA_SCHEME", default=env.str("OPA_SCHEME", default="http")
)
SOMABRAIN_OPA_URL = env.str("SOMABRAIN_OPA_URL", default="http://opa:8181")
SOMABRAIN_OPA_TIMEOUT = env.float("SOMABRAIN_OPA_TIMEOUT", default=2.0)
OPA_BUNDLE_PATH = env.str("OPA_BUNDLE_PATH", default="./opa")
# Fail-closed OPA is enforced in somabrain/opa/client.py. The legacy allow-on-error
# flag is intentionally unsupported; keep the variable only for backwards-compatible
# settings attribute migration.
SOMABRAIN_OPA_ALLOW_ON_ERROR = env.bool("SOMABRAIN_OPA_ALLOW_ON_ERROR", default=False)
SOMABRAIN_OPA_POLICY_KEY = env.str(
    "SOMABRAIN_OPA_POLICY_KEY", default="soma:opa:policy"
)
SOMABRAIN_OPA_POLICY_SIG_KEY = env.str(
    "SOMABRAIN_OPA_POLICY_SIG_KEY", default="soma:opa:policy:sig"
)

# Circuit breaker
SOMABRAIN_CIRCUIT_FAILURE_THRESHOLD = env.int(
    "SOMABRAIN_CIRCUIT_FAILURE_THRESHOLD", default=3
)
SOMABRAIN_CIRCUIT_RESET_INTERVAL = env.float(
    "SOMABRAIN_CIRCUIT_RESET_INTERVAL", default=60.0
)
SOMABRAIN_CIRCUIT_COOLDOWN_INTERVAL = env.float(
    "SOMABRAIN_CIRCUIT_COOLDOWN_INTERVAL", default=0.0
)

# Feature flags for infrastructure
SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS = env.bool(
    "SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS", default=True
)
REQUIRE_MEMORY = env.bool("REQUIRE_MEMORY", default=True)
REQUIRE_INFRA = env.str("REQUIRE_INFRA", default="1")
RUNNING_IN_DOCKER = env.bool("RUNNING_IN_DOCKER", default=False)

# ============================================================================
# CENTRALIZED CONNECTION DEFAULTS (Docker vs Local)
# ============================================================================
# If running in Docker (standalone), default to internal service names.
# If running locally, default to localhost ports.
# Explicit environment variables still override these fallbacks.

if RUNNING_IN_DOCKER:
    _KAFKA_DEFAULT = "somabrain_standalone_kafka:9092"
    _OPA_DEFAULT = "http://somabrain_standalone_opa:8181"
    # In standalone docker, Brain (30101) talks to SFM (10101) on host
    # via host.docker.internal gateway
    _MEMORY_DEFAULT = "http://host.docker.internal:10101"
    _REDIS_DEFAULT = "redis://somabrain_standalone_redis:6379/0"
else:
    _KAFKA_DEFAULT = "127.0.0.1:9092"
    _OPA_DEFAULT = "http://127.0.0.1:8181"
    _MEMORY_DEFAULT = "http://127.0.0.1:10101"
    _REDIS_DEFAULT = "redis://127.0.0.1:6379/0"

# Kafka
# ----------------------------------------------------------------------------
SOMABRAIN_KAFKA_URL = env.str("SOMABRAIN_KAFKA_URL", default=_KAFKA_DEFAULT)
# Bootstrap servers often mirror URL
KAFKA_BOOTSTRAP_SERVERS = env.str(
    "KAFKA_BOOTSTRAP_SERVERS", default=SOMABRAIN_KAFKA_URL
).replace("kafka://", "")

SOMABRAIN_KAFKA_HOST = env.str(
    "SOMABRAIN_KAFKA_HOST", default=env.str("KAFKA_HOST", default=None)
)
SOMABRAIN_KAFKA_PORT = env.int(
    "SOMABRAIN_KAFKA_PORT", default=env.int("KAFKA_PORT", default=0)
)
SOMABRAIN_KAFKA_SCHEME = env.str(
    "SOMABRAIN_KAFKA_SCHEME", default=env.str("KAFKA_SCHEME", default="kafka")
)
# Alias for consistency
SOMA_KAFKA_BOOTSTRAP = env.str("SOMA_KAFKA_BOOTSTRAP", default=SOMABRAIN_KAFKA_URL)

KAFKA_GROUP_ID = env.str("KAFKA_GROUP_ID", default=None)
SOMABRAIN_CONSUMER_GROUP = env.str(
    "SOMABRAIN_CONSUMER_GROUP", default="orchestrator-service"
)

# OPA
# ----------------------------------------------------------------------------
SOMABRAIN_OPA_URL = env.str("SOMABRAIN_OPA_URL", default=_OPA_DEFAULT)

SOMABRAIN_OPA_HOST = env.str(
    "SOMABRAIN_OPA_HOST", default=env.str("OPA_HOST", default=None)
)
SOMABRAIN_OPA_PORT = env.int(
    "SOMABRAIN_OPA_PORT", default=env.int("OPA_PORT", default=0)
)
SOMABRAIN_OPA_SCHEME = env.str(
    "SOMABRAIN_OPA_SCHEME", default=env.str("OPA_SCHEME", default="http")
)
SOMABRAIN_OPA_TIMEOUT = env.float("SOMABRAIN_OPA_TIMEOUT", default=2.0)
OPA_BUNDLE_PATH = env.str("OPA_BUNDLE_PATH", default="./opa")
SOMABRAIN_OPA_POLICY_KEY = env.str(
    "SOMABRAIN_OPA_POLICY_KEY", default="soma:opa:policy"
)
SOMABRAIN_OPA_POLICY_SIG_KEY = env.str(
    "SOMABRAIN_OPA_POLICY_SIG_KEY", default="soma:opa:policy:sig"
)

# URLs used by the legacy /health aggregator in somabrain/config/urls.py.
# These are intentionally separate from the canonical SOMABRAIN_*_URL settings
# so existing health checks keep working without touching every call site.
OPA_URL = env.str("OPA_URL", default=SOMABRAIN_OPA_URL)
MINIO_ENDPOINT = env.str("MINIO_ENDPOINT", default="http://minio:9000")
SCHEMA_REGISTRY_URL = env.str(
    "SCHEMA_REGISTRY_URL", default="http://somabrain_standalone_schema_registry:8081"
)

# External Memory (SFM)
# ----------------------------------------------------------------------------
SOMABRAIN_MEMORY_HTTP_ENDPOINT = env.str(
    "SOMABRAIN_MEMORY_HTTP_ENDPOINT", default=_MEMORY_DEFAULT
)
SOMABRAIN_MEMORY_HTTP_TOKEN = env.str("SOMABRAIN_MEMORY_HTTP_TOKEN", default="")
if REQUIRE_MEMORY and not SOMABRAIN_MEMORY_HTTP_TOKEN:
    raise environ.ImproperlyConfigured(
        "SOMABRAIN_MEMORY_HTTP_TOKEN must be set when REQUIRE_MEMORY is enabled."
    )
SOMABRAIN_HTTP_KEEPALIVE = env.int("SOMABRAIN_HTTP_KEEPALIVE", default=32)
SOMABRAIN_HTTP_RETRIES = env.int("SOMABRAIN_HTTP_RETRIES", default=1)

# Service configuration
HOME_DIR = env.str("HOME", default="")
SOMABRAIN_HOST = env.str("SOMABRAIN_HOST", default="0.0.0.0")
SOMABRAIN_PORT = env.str("SOMABRAIN_PORT", default="30101")
SOMABRAIN_HOST_PORT = env.int("SOMABRAIN_HOST_PORT", default=30101)
SOMABRAIN_WORKERS = env.int("SOMABRAIN_WORKERS", default=1)
SOMABRAIN_SERVICE_NAME = env.str("SOMABRAIN_SERVICE_NAME", default="somabrain")
SOMABRAIN_NAMESPACE = env.str("SOMABRAIN_NAMESPACE", default="public")
SOMABRAIN_DEFAULT_TENANT = env.str("SOMABRAIN_DEFAULT_TENANT", default="public")
SOMABRAIN_TENANT_ID = env.str("SOMABRAIN_TENANT_ID", default="default")

# URLs
SOMABRAIN_API_URL = env.str("SOMABRAIN_API_URL", default="")
SOMABRAIN_DEFAULT_BASE_URL = env.str(
    "SOMABRAIN_DEFAULT_BASE_URL", default="http://127.0.0.1:30101"
)
BASE_URL = env.str("BASE_URL", default="")
SUPERVISOR_URL = env.str("SUPERVISOR_URL", default=None)
SUPERVISOR_HTTP_USER = env.str("SUPERVISOR_HTTP_USER", default="admin")
SUPERVISOR_HTTP_PASS = env.str("SUPERVISOR_HTTP_PASS", default="")
INTEGRATOR_URL = env.str("INTEGRATOR_URL", default=None)
SEGMENTATION_URL = env.str("SEGMENTATION_URL", default=None)
OTEL_EXPORTER_OTLP_ENDPOINT = env.str("OTEL_EXPORTER_OTLP_ENDPOINT", default="")

# Health endpoints
SOMABRAIN_HEALTH_PORT = env.int("HEALTH_PORT", default=None)
SOMABRAIN_INTEGRATOR_HEALTH_PORT = env.int(
    "SOMABRAIN_INTEGRATOR_HEALTH_PORT", default=9015
)
SOMABRAIN_INTEGRATOR_HEALTH_URL = env.str(
    "SOMABRAIN_INTEGRATOR_HEALTH_URL",
    default="http://somabrain_integrator_triplet:9015/health",
)
SOMABRAIN_SEGMENTATION_HEALTH_URL = env.str(
    "SOMABRAIN_SEGMENTATION_HEALTH_URL", default="http://somabrain_cog:9016/health"
)

# Outbox
OUTBOX_BATCH_SIZE = env.int("OUTBOX_BATCH_SIZE", default=100)
OUTBOX_MAX_DELAY = env.float("OUTBOX_MAX_DELAY", default=5.0)
OUTBOX_MAX_RETRIES = env.int("OUTBOX_MAX_RETRIES", default=5)
OUTBOX_POLL_INTERVAL = env.float("OUTBOX_POLL_INTERVAL", default=1.0)
OUTBOX_PRODUCER_RETRY_MS = env.int("OUTBOX_PRODUCER_RETRY_MS", default=1000)
OUTBOX_API_TOKEN = env.str("OUTBOX_API_TOKEN", default="")

# Journal
SOMABRAIN_JOURNAL_DIR = env.str(
    "SOMABRAIN_JOURNAL_DIR", default="/tmp/somabrain_journal"
)
JOURNAL_REPLAY_INTERVAL = env.int("JOURNAL_REPLAY_INTERVAL", default=300)
SOMABRAIN_JOURNAL_MAX_FILE_SIZE = env.int(
    "SOMABRAIN_JOURNAL_MAX_FILE_SIZE", default=104857600
)
SOMABRAIN_JOURNAL_MAX_FILES = env.int("SOMABRAIN_JOURNAL_MAX_FILES", default=10)
SOMABRAIN_JOURNAL_ROTATION_INTERVAL = env.int(
    "SOMABRAIN_JOURNAL_ROTATION_INTERVAL", default=86400
)
SOMABRAIN_JOURNAL_RETENTION_DAYS = env.int(
    "SOMABRAIN_JOURNAL_RETENTION_DAYS", default=7
)
SOMABRAIN_JOURNAL_COMPRESSION = env.bool("SOMABRAIN_JOURNAL_COMPRESSION", default=True)
SOMABRAIN_JOURNAL_SYNC_WRITES = env.bool("SOMABRAIN_JOURNAL_SYNC_WRITES", default=True)

# Test environment
PYTEST_CURRENT_TEST = env.str("PYTEST_CURRENT_TEST", default=None)
OAK_TEST_MODE = env.bool("OAK_TEST_MODE", default=False)

# Documentation build detection
SPHINX_BUILD = env.bool("SPHINX_BUILD", default=False)
