"""Infrastructure settings and connection defaults for SomaBrain.

Secret resolution (VIBE Rule 164, zero-trust):

  1. A secret is read from Vault and held in this module. It is NEVER
     written to ``os.environ``. A secret in the process environment is a
     secret in ``ps``, in ``/proc/*/environ`` and in every crash dump.
  2. Environment variables carry TOPOLOGY only - hosts, ports, URLs, modes.
  3. A missing credential fails closed. There is no local copy to fall
     back on, and no empty string dressed up as a default.
"""

import os

import environ  # type: ignore[import-untyped]

env = environ.Env()

# ============================================================================
# INFRASTRUCTURE SETTINGS
# ============================================================================

# Values resolved from Vault at import time, held here and nowhere else.
# Nothing in this module writes these into os.environ.
_RESOLVED: dict[str, str] = {}


def _resolved(name: str) -> str:
    """Return a Vault-resolved secret, or "" when it was not provisioned."""
    return _RESOLVED.get(name, "")


def configure_tf_metal() -> None:
    """Pin TensorFlow/Metal device-handling behavior.

    TensorFlow/Metal can trigger device-handling crashes on some macOS hosts.
    Pinning this before downstream imports keeps local diagnostics reproducible.
    """
    os.environ.setdefault("TF_METAL_DEVICE_HANDLING", "1")


def _remember(name: str, value: object | None) -> None:
    """Hold a Vault-resolved secret in this module. Never touches environ."""
    if value is None:
        return
    text = str(value).strip()
    if text:
        _RESOLVED[name] = text


def configure_infra_secrets() -> None:
    """Resolve infrastructure secrets from Vault into module state.

    The values land in ``_RESOLVED`` and are read by the settings below.
    They are never exported to the process environment - Rule 164.

    Vault being unreachable is not "use the environment instead". The
    callers that need these secrets fail closed when they are absent.
    """
    try:
        from somabrain.core.security.vault_client import (
            SecretNotFound,
            VaultNotConfigured,
            get_db_credentials,
            get_runtime_secrets,
            get_secret,
        )
    except ImportError:
        return

    # Each secret is independent: one missing document must not abort the
    # others. A secret that is absent stays absent and the feature that needs
    # it fails closed (Rule 91). A Vault *outage* is not "secrets unavailable"
    # for the rest — only that lookup is skipped, and the caller refuses.
    def _try(fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except (SecretNotFound, VaultNotConfigured):
            return None

    db_creds = _try(get_db_credentials)
    # Expected shape: username/password/host/port/dbname. Absent topology
    # is not invented: there is no 127.0.0.1 or 5432 fallback here.
    if db_creds:
        _user = db_creds.get("username")
        _pass = db_creds.get("password")
        _host = db_creds.get("host")
        _port = db_creds.get("port")
        _name = db_creds.get("dbname")
        if _user and _pass and _host and _port and _name:
            _remember(
                "SOMABRAIN_POSTGRES_DSN",
                f"postgres://{_user}:{_pass}@{_host}:{_port}/{_name}",
            )

    redis_creds = _try(get_secret, "somabrain/redis")
    if redis_creds:
        _remember("SOMABRAIN_REDIS_URL", redis_creds.get("url"))

    runtime_secrets = _try(get_runtime_secrets)
    if runtime_secrets:
        _remember(
            "SOMABRAIN_MEMORY_HTTP_TOKEN",
            runtime_secrets.get("memory_http_token"),
        )
        _remember(
            "SUPERVISOR_HTTP_PASS",
            runtime_secrets.get("supervisor_http_pass"),
        )
        _remember("OUTBOX_API_TOKEN", runtime_secrets.get("api_token"))
        _remember("SOMABRAIN_API_TOKEN", runtime_secrets.get("api_token"))
        _remember("SOMA_API_TOKEN", runtime_secrets.get("api_token"))
        _remember(
            "SOMABRAIN_PROVENANCE_SECRET",
            runtime_secrets.get("provenance_secret"),
        )


# Resolve Vault secrets BEFORE the settings below read `_resolved`. Calling
# this at import time is what makes the Vault path real: the previous order
# (configure_* after this module was imported) left `_RESOLVED` empty and the
# assignments fell through to ENV — a secret in ENV, which Rule 164 forbids.
configure_infra_secrets()

# Secret-bearing DSN: Vault only (somabrain/database). ENV never carries a
# DSN — a DSN is a password (Rule 164). Assembled in configure_infra_secrets.
SOMABRAIN_POSTGRES_DSN = _resolved("SOMABRAIN_POSTGRES_DSN")
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
# Redis URL may embed a password, so when Vault has it Vault is authoritative.
# An empty value means unset; readers fail closed.
SOMABRAIN_REDIS_URL = _resolved("SOMABRAIN_REDIS_URL")
# Host is topology: no localhost default. Empty means unset; readers fail closed.
SOMABRAIN_REDIS_HOST = env.str("SOMABRAIN_REDIS_HOST", default="")
SOMABRAIN_REDIS_PORT = _parse_port(env.str("SOMABRAIN_REDIS_PORT", default=None), 6379)
SOMABRAIN_REDIS_DB = env.int("SOMABRAIN_REDIS_DB", default=0)

# Kafka, OPA, Redis and Memory are declared once, below, under
# "CENTRALIZED CONNECTION DEFAULTS". Two blocks that both assign
# SOMABRAIN_OPA_URL disagree the moment an operator looks at one of them.

# Milvus
SOMABRAIN_MILVUS_HOST = env.str(
    "MILVUS_HOST", default=env.str("SOMABRAIN_MILVUS_HOST", default=None)
)
SOMABRAIN_MILVUS_PORT = env.int("MILVUS_PORT", default=env.int("SOMABRAIN_MILVUS_PORT", default=None) or 0)
SOMABRAIN_MILVUS_COLLECTION = env.str("MILVUS_COLLECTION", default="oak_options")
MILVUS_SEGMENT_REFRESH_INTERVAL = env.float(
    "MILVUS_SEGMENT_REFRESH_INTERVAL", default=60.0
)
MILVUS_LATENCY_WINDOW = env.int("MILVUS_LATENCY_WINDOW", default=50)

# Fail-closed OPA is enforced in somabrain/opa/client.py. The legacy allow-on-error
# flag is intentionally unsupported; keep the variable only for backwards-compatible
# settings attribute migration. The OPA URL itself is declared once, below.
SOMABRAIN_OPA_ALLOW_ON_ERROR = env.bool("SOMABRAIN_OPA_ALLOW_ON_ERROR", default=False)

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
# SERVICE TOPOLOGY (no code defaults)
# ============================================================================
# A deployment URL has no code default. There is no Docker-vs-local fallback
# block: a silent 127.0.0.1 or host.docker.internal is a URL an operator cannot
# change and a reviewer cannot see (Rule 91). The operator names each endpoint
# in deployment env / Compose / Helm. Readers use
# somabrain.settings.resolve.require_url / optional_url, which fail closed.

# Kafka
# ----------------------------------------------------------------------------
SOMABRAIN_KAFKA_URL = env.str("SOMABRAIN_KAFKA_URL", default="")
# Bootstrap servers often mirror URL
KAFKA_BOOTSTRAP_SERVERS = env.str("KAFKA_BOOTSTRAP_SERVERS", default="").replace(
    "kafka://", ""
)

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
SOMA_KAFKA_BOOTSTRAP = env.str("SOMA_KAFKA_BOOTSTRAP", default=SOMABRAIN_KAFKA_URL or "")

KAFKA_GROUP_ID = env.str("KAFKA_GROUP_ID", default=None)
SOMABRAIN_CONSUMER_GROUP = env.str(
    "SOMABRAIN_CONSUMER_GROUP", default="orchestrator-service"
)

# OPA
# ----------------------------------------------------------------------------
SOMABRAIN_OPA_URL = env.str("SOMABRAIN_OPA_URL", default="")

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
# No code default: empty means unset and the reader fails closed.
OPA_URL = env.str("OPA_URL", default=SOMABRAIN_OPA_URL or "")
MINIO_ENDPOINT = env.str("MINIO_ENDPOINT", default="")
SCHEMA_REGISTRY_URL = env.str("SCHEMA_REGISTRY_URL", default="")
SOMABRAIN_AUTH_URL = env.str("SOMABRAIN_AUTH_URL", default="")

# External Memory (SFM)
# ----------------------------------------------------------------------------
SOMABRAIN_MEMORY_HTTP_ENDPOINT = env.str("SOMABRAIN_MEMORY_HTTP_ENDPOINT", default="")

# Legacy alias used by somabrain/config/urls.py and system_health.py health checks.
SOMA_FRACTAL_MEMORY_URL = env.str(
    "SOMA_FRACTAL_MEMORY_URL", default=SOMABRAIN_MEMORY_HTTP_ENDPOINT or ""
)
# Secret: Vault only (secret/agent/credentials[somabrain_memory_http_token]).
# There is deliberately no ENV read here. A token in ENV is a token in `ps`,
# in /proc/*/environ and in every crash dump — Rule 164. Missing is a refusal.
SOMABRAIN_MEMORY_HTTP_TOKEN = _resolved("SOMABRAIN_MEMORY_HTTP_TOKEN")
if REQUIRE_MEMORY and not SOMABRAIN_MEMORY_HTTP_TOKEN:
    raise environ.ImproperlyConfigured(
        "SOMABRAIN_MEMORY_HTTP_TOKEN must be provisioned via Vault "
        "(secret/agent/credentials[somabrain_memory_http_token]). It is never "
        "read from the environment and there is no default (Rule 164 / Rule 91)."
    )
SOMABRAIN_HTTP_KEEPALIVE = env.int("SOMABRAIN_HTTP_KEEPALIVE", default=32)
SOMABRAIN_HTTP_RETRIES = env.int("SOMABRAIN_HTTP_RETRIES", default=1)

# Service configuration
HOME_DIR = env.str("HOME", default="")
SOMABRAIN_HOST = env.str("SOMABRAIN_HOST", default="")
SOMABRAIN_PORT = env.str("SOMABRAIN_PORT", default="")
SOMABRAIN_HOST_PORT = _parse_port(env.str("SOMABRAIN_HOST_PORT", default=None), 0)
SOMABRAIN_WORKERS = env.int("SOMABRAIN_WORKERS", default=1)
SOMABRAIN_SERVICE_NAME = env.str("SOMABRAIN_SERVICE_NAME", default="somabrain")
SOMABRAIN_NAMESPACE = env.str("SOMABRAIN_NAMESPACE", default="")
SOMABRAIN_DEFAULT_TENANT = env.str("SOMABRAIN_DEFAULT_TENANT", default="")
# No ``"default"`` partition: an unset tenant id stays unset and the
# resolution path raises (Rule 91). ``standalone.py`` pins its own identity.
SOMABRAIN_TENANT_ID = env.str("SOMABRAIN_TENANT_ID", default="")

# URLs. A missing URL is left missing: the resolver
# (somabrain.settings.resolve.require_url / optional_url) is the only reader
# and it fails closed. No localhost and no cluster DNS at the declaration site
# outside the Docker-vs-local block above.
SOMABRAIN_API_URL = env.str("SOMABRAIN_API_URL", default="")
SOMABRAIN_DEFAULT_BASE_URL = env.str("SOMABRAIN_DEFAULT_BASE_URL", default="")
BASE_URL = env.str("BASE_URL", default="")
SUPERVISOR_URL = env.str("SUPERVISOR_URL", default=None)
SUPERVISOR_HTTP_USER = env.str("SUPERVISOR_HTTP_USER", default="admin")
# Secret: Vault only (somabrain/runtime[supervisor_http_pass]). No ENV, no "".
SUPERVISOR_HTTP_PASS = _resolved("SUPERVISOR_HTTP_PASS")
INTEGRATOR_URL = env.str("INTEGRATOR_URL", default=None)
SEGMENTATION_URL = env.str("SEGMENTATION_URL", default=None)
OTEL_EXPORTER_OTLP_ENDPOINT = env.str("OTEL_EXPORTER_OTLP_ENDPOINT", default="")

# gRPC transport (NET binding). File *paths* are topology; the credentials
# they name live in Vault or on a mounted secret volume — never in ENV.
SOMABRAIN_GRPC_CERT_FILE = env.str("SOMABRAIN_GRPC_CERT_FILE", default="")
SOMABRAIN_GRPC_KEY_FILE = env.str("SOMABRAIN_GRPC_KEY_FILE", default="")
SOMABRAIN_GRPC_LISTEN_HOST = env.str("SOMABRAIN_GRPC_LISTEN_HOST", default="0.0.0.0")
SOMABRAIN_GRPC_LISTEN_PORT = env.int("SOMABRAIN_GRPC_LISTEN_PORT", default=30102)

# Health endpoints
SOMABRAIN_HEALTH_PORT = env.int("HEALTH_PORT", default=None)
SOMABRAIN_INTEGRATOR_HEALTH_PORT = env.int(
    "SOMABRAIN_INTEGRATOR_HEALTH_PORT", default=9015
)
SOMABRAIN_INTEGRATOR_HEALTH_URL = env.str("SOMABRAIN_INTEGRATOR_HEALTH_URL", default="")
SOMABRAIN_SEGMENTATION_HEALTH_URL = env.str(
    "SOMABRAIN_SEGMENTATION_HEALTH_URL", default=""
)

# Outbox
OUTBOX_BATCH_SIZE = env.int("OUTBOX_BATCH_SIZE", default=100)
OUTBOX_MAX_DELAY = env.float("OUTBOX_MAX_DELAY", default=5.0)
OUTBOX_MAX_RETRIES = env.int("OUTBOX_MAX_RETRIES", default=5)
OUTBOX_POLL_INTERVAL = env.float("OUTBOX_POLL_INTERVAL", default=1.0)
OUTBOX_PRODUCER_RETRY_MS = env.int("OUTBOX_PRODUCER_RETRY_MS", default=1000)
# Secret: Vault only (somabrain/runtime[api_token]). No ENV, no "".
OUTBOX_API_TOKEN = _resolved("OUTBOX_API_TOKEN")

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
