"""
Django settings for somabrain project.

Generated from legacy Pydantic settings files - django-environ migration.
All configuration loaded from environment variables.
"""

from pathlib import Path
import environ

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# Initialize django-environ
env = environ.Env(
    # Django core settings
    DEBUG=(bool, False),
    SECRET_KEY=(str, "django-insecure-change-me-locally-somabrain"),
    ALLOWED_HOSTS=(list, ["*"]),
    # SomaBrain core settings with defaults
    SOMABRAIN_LOG_LEVEL=(str, "INFO"),
    SOMABRAIN_POSTGRES_DSN=(str, ""),
)

# Read .env file
environ.Env.read_env(BASE_DIR / ".env")

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("SOMABRAIN_JWT_SECRET", default=env("SECRET_KEY"))

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env("SOMABRAIN_LOG_LEVEL") == "DEBUG"

ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "somabrain",  # Main app
    "somabrain.saas",  # SaaS: tenants, subscriptions, API keys
    "ninja",  # Django Ninja
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "somabrain.controls.security_middleware.SecurityMiddleware",
    "somabrain.controls.cognitive_middleware.CognitiveMiddleware",
    "somabrain.controls.django_middleware.ControlsMiddleware",
    "somabrain.controls.opa_middleware.OpaMiddleware",
]

ROOT_URLCONF = "somabrain.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "somabrain.wsgi.application"

# Database - PostgreSQL only
DATABASES = {
    "default": env.db(
        "SOMABRAIN_POSTGRES_DSN", default="postgresql://localhost/somabrain"
    )
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "static/"

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ============================================================================
# SOMABRAIN CONFIGURATION - All Environment Variables
# ============================================================================

# --- AUTH & SECURITY SETTINGS ---
SOMABRAIN_AUTH_REQUIRED = env.bool("SOMABRAIN_AUTH_REQUIRED", default=False)
SOMABRAIN_API_TOKEN = env.str("SOMABRAIN_API_TOKEN", default=None)
SOMABRAIN_AUTH_SERVICE_URL = env.str("SOMABRAIN_AUTH_SERVICE_URL", default=None)
SOMABRAIN_AUTH_SERVICE_API_KEY = env.str("SOMABRAIN_AUTH_SERVICE_API_KEY", default=None)
SOMABRAIN_JWT_SECRET = env.str("SOMABRAIN_JWT_SECRET", default=None)
SOMABRAIN_JWT_PUBLIC_KEY_PATH = env.str("SOMABRAIN_JWT_PUBLIC_KEY_PATH", default=None)
SOMABRAIN_JWT_AUDIENCE = env.str("SOMABRAIN_JWT_AUDIENCE", default=None)
SOMABRAIN_JWT_ISSUER = env.str("SOMABRAIN_JWT_ISSUER", default=None)

# OPA keys
SOMABRAIN_OPA_PRIVKEY_PATH = env.str("SOMABRAIN_OPA_PRIVKEY_PATH", default=None)
SOMABRAIN_OPA_PUBKEY_PATH = env.str("SOMABRAIN_OPA_PUBKEY_PATH", default=None)

# Provenance
SOMABRAIN_PROVENANCE_SECRET = env.str("SOMABRAIN_PROVENANCE_SECRET", default=None)
SOMABRAIN_PROVENANCE_STRICT_DENY = env.bool(
    "SOMABRAIN_PROVENANCE_STRICT_DENY", default=False
)
SOMABRAIN_REQUIRE_PROVENANCE = env.bool("SOMABRAIN_REQUIRE_PROVENANCE", default=False)

# Vault integration
SOMABRAIN_VAULT_ADDR = env.str("VAULT_ADDR", default=None)
SOMABRAIN_VAULT_TOKEN = env.str("VAULT_TOKEN", default=None)
SOMABRAIN_VAULT_PUBKEY_PATH = env.str("SOMABRAIN_VAULT_PUBKEY_PATH", default=None)

# Constitution
SOMABRAIN_CONSTITUTION_PUBKEYS = env.str("SOMABRAIN_CONSTITUTION_PUBKEYS", default=None)
SOMABRAIN_CONSTITUTION_PUBKEY_PATH = env.str(
    "SOMABRAIN_CONSTITUTION_PUBKEY_PATH", default=None
)
SOMABRAIN_CONSTITUTION_PRIVKEY_PATH = env.str(
    "SOMABRAIN_CONSTITUTION_PRIVKEY_PATH", default=None
)
SOMABRAIN_CONSTITUTION_THRESHOLD = env.int(
    "SOMABRAIN_CONSTITUTION_THRESHOLD", default=1
)
SOMABRAIN_CONSTITUTION_SIGNER_ID = env.str(
    "SOMABRAIN_CONSTITUTION_SIGNER_ID", default="default"
)

# Feature flags
SOMABRAIN_MINIMAL_PUBLIC_API = env.bool("SOMABRAIN_MINIMAL_PUBLIC_API", default=False)
SOMABRAIN_ALLOW_ANONYMOUS_TENANTS = env.bool(
    "SOMABRAIN_ALLOW_ANONYMOUS_TENANTS", default=False
)
SOMABRAIN_BLOCK_UA_REGEX = env.str("SOMABRAIN_BLOCK_UA_REGEX", default="")
SOMABRAIN_KILL_SWITCH = env.bool("SOMABRAIN_KILL_SWITCH", default=False)
SOMABRAIN_ALLOW_TINY_EMBEDDER = env.bool("SOMABRAIN_ALLOW_TINY_EMBEDDER", default=False)
SOMABRAIN_FEATURE_OVERRIDES = env.str(
    "SOMABRAIN_FEATURE_OVERRIDES", default="./data/feature_overrides.json"
)

# Cognitive threads
ENABLE_COG_THREADS = env.bool("ENABLE_COG_THREADS", default=False)
COGNITIVE_THREAD_DEFAULT_CURSOR = 0

# Orchestrator
SOMABRAIN_ORCH_CONSUMER_GROUP = env.str(
    "SOMABRAIN_ORCH_CONSUMER_GROUP", default="orchestrator-service"
)
SOMABRAIN_ORCH_NAMESPACE = env.str("SOMABRAIN_ORCH_NAMESPACE", default="cog")
SOMABRAIN_ORCH_ROUTING = env.str("SOMABRAIN_ORCH_ROUTING", default="")

# Teach feedback
TEACH_FEEDBACK_PROC_PORT = env.int("TEACH_FEEDBACK_PROC_PORT", default=8086)
TEACH_PROC_GROUP = env.str("TEACH_PROC_GROUP", default="teach-feedback-proc")
TEACH_DEDUP_CACHE_SIZE = env.int("TEACH_DEDUP_CACHE_SIZE", default=512)

# Feature flags service
SOMABRAIN_FEATURE_FLAGS_PORT = env.int("SOMABRAIN_FEATURE_FLAGS_PORT", default=9697)

# Universe
SOMABRAIN_UNIVERSE = env.str("SOMA_UNIVERSE", default=None)

# Reward
SOMABRAIN_REWARD_PORT = env.int("SOMABRAIN_REWARD_PORT", default=8083)
SOMABRAIN_REWARD_PRODUCER_PORT = env.int("REWARD_PRODUCER_PORT", default=30183)
SOMABRAIN_REWARD_PRODUCER_HOST_PORT = env.int(
    "REWARD_PRODUCER_HOST_PORT", default=30183
)

# Benchmark
SOMABRAIN_BENCH_TIMEOUT = env.float("BENCH_TIMEOUT", default=90.0)

# --- INFRASTRUCTURE SETTINGS ---
# PostgreSQL
SOMABRAIN_POSTGRES_DSN = env.str("SOMABRAIN_POSTGRES_DSN", default="")
DATABASE_URL = env.str("DATABASE_URL", default=None)

# Redis
SOMABRAIN_REDIS_URL = env.str(
    "SOMABRAIN_REDIS_URL", default=env.str("REDIS_URL", default="")
)
SOMABRAIN_REDIS_HOST = env.str(
    "SOMABRAIN_REDIS_HOST", default=env.str("REDIS_HOST", default=None)
)
SOMABRAIN_REDIS_PORT = env.int(
    "SOMABRAIN_REDIS_PORT", default=env.int("REDIS_PORT", default=6379)
)
SOMABRAIN_REDIS_DB = env.int(
    "SOMABRAIN_REDIS_DB", default=env.int("REDIS_DB", default=0)
)

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
SOMABRAIN_OPA_URL = env.str("SOMABRAIN_OPA_URL", default="http://localhost:20181")
SOMABRAIN_OPA_ALLOW_ON_ERROR = env.bool("SOMABRAIN_OPA_ALLOW_ON_ERROR", default=False)
SOMABRAIN_OPA_POLICY_KEY = env.str(
    "SOMABRAIN_OPA_POLICY_KEY", default="soma/policy/integrator/allow"
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

# HTTP client settings
SOMABRAIN_HTTP_MAX_CONNS = env.int("SOMABRAIN_HTTP_MAX_CONNS", default=64)
SOMABRAIN_HTTP_KEEPALIVE = env.int("SOMABRAIN_HTTP_KEEPALIVE", default=32)
SOMABRAIN_HTTP_RETRIES = env.int("SOMABRAIN_HTTP_RETRIES", default=1)

# Logging and metrics - /app/logs is tmpfs in Docker, compatible with read-only rootfs
SOMABRAIN_LOG_PATH = env.str("SOMABRAIN_LOG_PATH", default="/app/logs/somabrain.log")
SOMABRAIN_LOG_LEVEL = env.str("SOMABRAIN_LOG_LEVEL", default="INFO")
SOMABRAIN_METRICS_SINK = env.str("SOMABRAIN_METRICS_SINK", default=None)
SOMABRAIN_LOG_CONFIG = env.str(
    "SOMABRAIN_LOG_CONFIG", default="/app/config/logging.yaml"
)

# Service configuration
HOME_DIR = env.str("HOME", default="")
SOMABRAIN_HOST = env.str("SOMABRAIN_HOST", default="0.0.0.0")
SOMABRAIN_PORT = env.str("SOMABRAIN_PORT", default="9696")
SOMABRAIN_HOST_PORT = env.int("SOMABRAIN_HOST_PORT", default=9696)
SOMABRAIN_WORKERS = env.int("SOMABRAIN_WORKERS", default=1)
SOMABRAIN_SERVICE_NAME = env.str("SOMABRAIN_SERVICE_NAME", default="somabrain")
SOMABRAIN_NAMESPACE = env.str("SOMABRAIN_NAMESPACE", default="public")
SOMABRAIN_DEFAULT_TENANT = env.str("SOMABRAIN_DEFAULT_TENANT", default="public")
SOMABRAIN_TENANT_ID = env.str("SOMABRAIN_TENANT_ID", default="default")

# URLs
SOMABRAIN_API_URL = env.str("SOMABRAIN_API_URL", default="")
SOMABRAIN_DEFAULT_BASE_URL = env.str(
    "SOMABRAIN_DEFAULT_BASE_URL", default="http://localhost:9696"
)
BASE_URL = env.str("BASE_URL", default="")
SUPERVISOR_URL = env.str("SUPERVISOR_URL", default=None)
SUPERVISOR_HTTP_USER = env.str("SUPERVISOR_HTTP_USER", default="admin")
SUPERVISOR_HTTP_PASS = env.str("SUPERVISOR_HTTP_PASS", default="soma")
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

# Kafka topics
SOMABRAIN_TOPIC_CONFIG_UPDATES = env.str(
    "SOMABRAIN_TOPIC_CONFIG_UPDATES", default="cog.config.updates"
)
SOMABRAIN_TOPIC_NEXT_EVENT = env.str(
    "SOMABRAIN_TOPIC_NEXT_EVENT", default="cog.next_event"
)
SOMABRAIN_TOPIC_STATE_UPDATES = env.str(
    "SOMABRAIN_TOPIC_STATE_UPDATES", default="cog.state.updates"
)
SOMABRAIN_TOPIC_AGENT_UPDATES = env.str(
    "SOMABRAIN_TOPIC_AGENT_UPDATES", default="cog.agent.updates"
)
SOMABRAIN_TOPIC_ACTION_UPDATES = env.str(
    "SOMABRAIN_TOPIC_ACTION_UPDATES", default="cog.action.updates"
)
SOMABRAIN_TOPIC_GLOBAL_FRAME = env.str(
    "SOMABRAIN_TOPIC_GLOBAL_FRAME", default="cog.global.frame"
)
SOMABRAIN_TOPIC_SEGMENTS = env.str("SOMABRAIN_TOPIC_SEGMENTS", default="cog.segments")
SOMABRAIN_AUDIT_TOPIC = env.str("SOMABRAIN_AUDIT_TOPIC", default="soma.audit")

# Outbox
OUTBOX_BATCH_SIZE = env.int("OUTBOX_BATCH_SIZE", default=100)
OUTBOX_MAX_DELAY = env.float("OUTBOX_MAX_DELAY", default=5.0)
OUTBOX_MAX_RETRIES = env.int("OUTBOX_MAX_RETRIES", default=5)
OUTBOX_POLL_INTERVAL = env.float("OUTBOX_POLL_INTERVAL", default=1.0)
OUTBOX_PRODUCER_RETRY_MS = env.int("OUTBOX_PRODUCER_RETRY_MS", default=1000)
OUTBOX_API_TOKEN = env.str(
    "OUTBOX_API_TOKEN", default=env.str("SOMA_API_TOKEN", default=None)
)

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

# CLI server settings
SOMABRAIN_CLI_HOST = env.str("HOST", default="0.0.0.0")
SOMABRAIN_CLI_PORT = env.int("PORT", default=8000)

# Mode configuration
SOMABRAIN_MODE = env.str("SOMABRAIN_MODE", default="full-local")

# --- MEMORY SETTINGS ---
# Memory HTTP service
SOMABRAIN_MEMORY_HTTP_HOST = env.str(
    "SOMABRAIN_MEMORY_HTTP_HOST", default=env.str("MEMORY_HTTP_HOST", default=None)
)
SOMABRAIN_MEMORY_HTTP_PORT = env.int(
    "SOMABRAIN_MEMORY_HTTP_PORT", default=env.int("MEMORY_HTTP_PORT", default=0)
)
SOMABRAIN_MEMORY_HTTP_SCHEME = env.str(
    "SOMABRAIN_MEMORY_HTTP_SCHEME",
    default=env.str("MEMORY_HTTP_SCHEME", default="http"),
)
SOMABRAIN_MEMORY_HTTP_ENDPOINT = env.str(
    "SOMABRAIN_MEMORY_HTTP_ENDPOINT",
    default=env.str("MEMORY_SERVICE_URL", default="http://localhost:9595"),
)
SOMABRAIN_MEMORY_HTTP_TOKEN = env.str("SOMABRAIN_MEMORY_HTTP_TOKEN", default=None)
SOMABRAIN_MEMORY_MAX = env.str("SOMABRAIN_MEMORY_MAX", default="10GB")
MEMORY_DB_PATH = env.str("MEMORY_DB_PATH", default="./data/memory.db")

# Memory weighting
SOMABRAIN_MEMORY_ENABLE_WEIGHTING = env.bool(
    "SOMABRAIN_FF_MEMORY_WEIGHTING",
    default=env.bool("SOMABRAIN_MEMORY_ENABLE_WEIGHTING", default=False),
)
SOMABRAIN_MEMORY_PHASE_PRIORS = env.str("SOMABRAIN_MEMORY_PHASE_PRIORS", default="")
SOMABRAIN_MEMORY_QUALITY_EXP = env.float("SOMABRAIN_MEMORY_QUALITY_EXP", default=1.0)
SOMABRAIN_MEMORY_FAST_ACK = env.bool("SOMABRAIN_MEMORY_FAST_ACK", default=False)

# Memory degradation
SOMABRAIN_MEMORY_DEGRADE_QUEUE = env.bool(
    "SOMABRAIN_MEMORY_DEGRADE_QUEUE", default=True
)
SOMABRAIN_MEMORY_DEGRADE_READONLY = env.bool(
    "SOMABRAIN_MEMORY_DEGRADE_READONLY", default=False
)
SOMABRAIN_MEMORY_DEGRADE_TOPIC = env.str(
    "SOMABRAIN_MEMORY_DEGRADE_TOPIC", default="memory.degraded"
)
SOMABRAIN_MEMORY_HEALTH_POLL_INTERVAL = env.float(
    "SOMABRAIN_MEMORY_HEALTH_POLL_INTERVAL", default=5.0
)
SOMABRAIN_DEBUG_MEMORY_CLIENT = env.bool("SOMABRAIN_DEBUG_MEMORY_CLIENT", default=False)

# Working memory configuration
SOMABRAIN_EMBED_DIM = env.int("EMBED_DIM", default=256)
SOMABRAIN_WM_SIZE = env.int("SOMABRAIN_WM_SIZE", default=64)
SOMABRAIN_WM_RECENCY_TIME_SCALE = env.float(
    "SOMABRAIN_WM_RECENCY_TIME_SCALE", default=1.0
)
SOMABRAIN_WM_RECENCY_MAX_STEPS = env.int("SOMABRAIN_WM_RECENCY_MAX_STEPS", default=1000)
SOMABRAIN_WM_ALPHA = env.float("SOMABRAIN_WM_ALPHA", default=0.6)
SOMABRAIN_WM_BETA = env.float("SOMABRAIN_WM_BETA", default=0.3)
SOMABRAIN_WM_GAMMA = env.float("SOMABRAIN_WM_GAMMA", default=0.1)
SOMABRAIN_WM_SALIENCE_THRESHOLD = env.float(
    "SOMABRAIN_WM_SALIENCE_THRESHOLD", default=0.4
)
SOMABRAIN_WM_PER_COL_MIN_CAPACITY = env.int(
    "SOMABRAIN_WM_PER_COL_MIN_CAPACITY", default=16
)
SOMABRAIN_WM_VOTE_SOFTMAX_FLOOR = env.float(
    "SOMABRAIN_WM_VOTE_SOFTMAX_FLOOR", default=1e-4
)
SOMABRAIN_WM_VOTE_ENTROPY_EPS = env.float("SOMABRAIN_WM_VOTE_ENTROPY_EPS", default=1e-9)
SOMABRAIN_WM_PER_TENANT_CAPACITY = env.int(
    "SOMABRAIN_WM_PER_TENANT_CAPACITY", default=128
)
SOMABRAIN_MTWM_MAX_TENANTS = env.int("SOMABRAIN_MTWM_MAX_TENANTS", default=1000)

# Micro-circuit configuration
SOMABRAIN_MICRO_CIRCUITS = env.int("SOMABRAIN_MICRO_CIRCUITS", default=1)
SOMABRAIN_MICRO_VOTE_TEMPERATURE = env.float(
    "SOMABRAIN_MICRO_VOTE_TEMPERATURE", default=0.25
)
SOMABRAIN_USE_MICROCIRCUITS = env.bool("SOMABRAIN_USE_MICROCIRCUITS", default=False)
SOMABRAIN_MICRO_MAX_TENANTS = env.int("SOMABRAIN_MICRO_MAX_TENANTS", default=1000)

# Tiered memory cleanup
SOMABRAIN_CLEANUP_BACKEND = env.str("SOMABRAIN_CLEANUP_BACKEND", default="milvus")
SOMABRAIN_CLEANUP_TOPK = env.int("SOMABRAIN_CLEANUP_TOPK", default=64)
SOMABRAIN_CLEANUP_HNSW_M = env.int("SOMABRAIN_CLEANUP_HNSW_M", default=32)
SOMABRAIN_CLEANUP_HNSW_EF_CONSTRUCTION = env.int(
    "SOMABRAIN_CLEANUP_HNSW_EF_CONSTRUCTION", default=200
)
SOMABRAIN_CLEANUP_HNSW_EF_SEARCH = env.int(
    "SOMABRAIN_CLEANUP_HNSW_EF_SEARCH", default=128
)

# Scorer weights
SOMABRAIN_SCORER_W_COSINE = env.float("SOMABRAIN_SCORER_W_COSINE", default=0.6)
SOMABRAIN_SCORER_W_FD = env.float("SOMABRAIN_SCORER_W_FD", default=0.25)
SOMABRAIN_SCORER_W_RECENCY = env.float("SOMABRAIN_SCORER_W_RECENCY", default=0.15)
SOMABRAIN_SCORER_WEIGHT_MIN = env.float("SOMABRAIN_SCORER_WEIGHT_MIN", default=0.0)
SOMABRAIN_SCORER_WEIGHT_MAX = env.float("SOMABRAIN_SCORER_WEIGHT_MAX", default=1.0)
SOMABRAIN_SCORER_RECENCY_TAU = env.float("SOMABRAIN_SCORER_RECENCY_TAU", default=32.0)

# Retrieval weights
SOMABRAIN_RETRIEVAL_ALPHA = env.float("SOMABRAIN_RETRIEVAL_ALPHA", default=1.0)
SOMABRAIN_RETRIEVAL_BETA = env.float("SOMABRAIN_RETRIEVAL_BETA", default=0.2)
SOMABRAIN_RETRIEVAL_GAMMA = env.float("SOMABRAIN_RETRIEVAL_GAMMA", default=0.1)
SOMABRAIN_RETRIEVAL_TAU = env.float("SOMABRAIN_RETRIEVAL_TAU", default=0.7)
SOMABRAIN_RECENCY_HALF_LIFE = env.float("SOMABRAIN_RECENCY_HALF_LIFE", default=60.0)
SOMABRAIN_RECENCY_SHARPNESS = env.float("SOMABRAIN_RECENCY_SHARPNESS", default=1.2)
SOMABRAIN_RECENCY_FLOOR = env.float("SOMABRAIN_RECENCY_FLOOR", default=0.05)
SOMABRAIN_DENSITY_TARGET = env.float("SOMABRAIN_DENSITY_TARGET", default=0.2)
SOMABRAIN_DENSITY_FLOOR = env.float("SOMABRAIN_DENSITY_FLOOR", default=0.6)
SOMABRAIN_DENSITY_WEIGHT = env.float("SOMABRAIN_DENSITY_WEIGHT", default=0.35)
SOMABRAIN_TAU_MIN = env.float("SOMABRAIN_TAU_MIN", default=0.4)
SOMABRAIN_TAU_MAX = env.float("SOMABRAIN_TAU_MAX", default=1.2)
SOMABRAIN_TAU_INC_UP = env.float("SOMABRAIN_TAU_INC_UP", default=0.1)
SOMABRAIN_TAU_INC_DOWN = env.float("SOMABRAIN_TAU_INC_DOWN", default=0.05)
SOMABRAIN_DUP_RATIO_THRESHOLD = env.float("SOMABRAIN_DUP_RATIO_THRESHOLD", default=0.5)

# Recall behavior
SOMABRAIN_RECALL_FULL_POWER = env.bool("SOMABRAIN_RECALL_FULL_POWER", default=True)
SOMABRAIN_RECALL_SIMPLE_DEFAULTS = env.bool(
    "SOMABRAIN_RECALL_SIMPLE_DEFAULTS", default=False
)
SOMABRAIN_RECALL_DEFAULT_RERANK = env.str(
    "SOMABRAIN_RECALL_DEFAULT_RERANK", default="auto"
)
SOMABRAIN_RECALL_DEFAULT_PERSIST = env.bool(
    "SOMABRAIN_RECALL_DEFAULT_PERSIST", default=True
)
SOMABRAIN_RECALL_DEFAULT_RETRIEVERS = env.str(
    "SOMABRAIN_RECALL_DEFAULT_RETRIEVERS", default="vector,wm,graph,lexical"
)

# Salience configuration
SOMABRAIN_SALIENCE_METHOD = env.str("SOMABRAIN_SALIENCE_METHOD", default="dense")
SOMABRAIN_SALIENCE_FD_RANK = env.int("SOMABRAIN_SALIENCE_FD_RANK", default=128)
SOMABRAIN_SALIENCE_FD_DECAY = env.float("SOMABRAIN_SALIENCE_FD_DECAY", default=0.9)
SOMABRAIN_SALIENCE_W_NOVELTY = env.float("SOMABRAIN_SALIENCE_W_NOVELTY", default=0.6)
SOMABRAIN_SALIENCE_W_ERROR = env.float("SOMABRAIN_SALIENCE_W_ERROR", default=0.4)
SOMABRAIN_SALIENCE_THRESHOLD_STORE = env.float(
    "SOMABRAIN_SALIENCE_THRESHOLD_STORE", default=0.5
)
SOMABRAIN_SALIENCE_THRESHOLD_ACT = env.float(
    "SOMABRAIN_SALIENCE_THRESHOLD_ACT", default=0.7
)
SOMABRAIN_SALIENCE_HYSTERESIS = env.float("SOMABRAIN_SALIENCE_HYSTERESIS", default=0.1)
SOMABRAIN_SALIENCE_FD_WEIGHT = env.float("SOMABRAIN_SALIENCE_FD_WEIGHT", default=0.25)
SOMABRAIN_SALIENCE_FD_ENERGY_FLOOR = env.float(
    "SOMABRAIN_SALIENCE_FD_ENERGY_FLOOR", default=0.9
)
SOMABRAIN_SALIENCE_SOFT_TEMPERATURE = env.float(
    "SOMABRAIN_SALIENCE_SOFT_TEMPERATURE", default=0.1
)
SOMABRAIN_USE_SOFT_SALIENCE = env.bool("SOMABRAIN_USE_SOFT_SALIENCE", default=False)

# Feature toggles
SOMABRAIN_USE_HRR = env.bool("SOMABRAIN_USE_HRR", default=False)
SOMABRAIN_USE_META_BRAIN = env.bool("SOMABRAIN_USE_META_BRAIN", default=False)
SOMABRAIN_USE_EXEC_CONTROLLER = env.bool("SOMABRAIN_USE_EXEC_CONTROLLER", default=False)
SOMABRAIN_USE_DRIFT_MONITOR = env.bool("SOMABRAIN_USE_DRIFT_MONITOR", default=False)
SOMABRAIN_USE_SDR_PREFILTER = env.bool("SOMABRAIN_USE_SDR_PREFILTER", default=False)
SOMABRAIN_USE_GRAPH_AUGMENT = env.bool("SOMABRAIN_USE_GRAPH_AUGMENT", default=False)
SOMABRAIN_USE_HRR_FIRST = env.bool("SOMABRAIN_USE_HRR_FIRST", default=False)

# Graph configuration
SOMABRAIN_GRAPH_HOPS = env.int("SOMABRAIN_GRAPH_HOPS", default=2)
SOMABRAIN_GRAPH_LIMIT = env.int("SOMABRAIN_GRAPH_LIMIT", default=20)
SOMABRAIN_GRAPH_FILE = env.str("SOMABRAIN_GRAPH_FILE", default=None)
SOMABRAIN_GRAPH_FILE_ACTION = env.str("SOMABRAIN_GRAPH_FILE_ACTION", default=None)
SOMABRAIN_GRAPH_FILE_AGENT = env.str("SOMABRAIN_GRAPH_FILE_AGENT", default=None)

# Planner / graph walk
SOMABRAIN_PLANNER_RWR_STEPS = env.int("SOMABRAIN_PLANNER_RWR_STEPS", default=20)
SOMABRAIN_PLANNER_RWR_RESTART = env.float("SOMABRAIN_PLANNER_RWR_RESTART", default=0.15)
SOMABRAIN_PLANNER_RWR_MAX_NODES = env.int(
    "SOMABRAIN_PLANNER_RWR_MAX_NODES", default=128
)
SOMABRAIN_PLANNER_RWR_EDGES_PER_NODE = env.int(
    "SOMABRAIN_PLANNER_RWR_EDGES_PER_NODE", default=32
)
SOMABRAIN_PLANNER_RWR_MAX_ITEMS = env.int("SOMABRAIN_PLANNER_RWR_MAX_ITEMS", default=5)

# Rate limiting
SOMABRAIN_RATE_RPS = env.int("SOMABRAIN_RATE_RPS", default=1000)
SOMABRAIN_RATE_BURST = env.int("SOMABRAIN_RATE_BURST", default=2000)
SOMABRAIN_WRITE_DAILY_LIMIT = env.int("SOMABRAIN_WRITE_DAILY_LIMIT", default=100000)

# --- LEARNING & ADAPTATION SETTINGS ---
# Tau / entropy tuning
SOMABRAIN_TAU_DECAY_ENABLED = env.bool("SOMABRAIN_TAU_DECAY_ENABLED", default=False)
SOMABRAIN_TAU_DECAY_RATE = env.float("SOMABRAIN_TAU_DECAY_RATE", default=0.0)
SOMABRAIN_TAU_ANNEAL_MODE = env.str("SOMABRAIN_TAU_ANNEAL_MODE", default=None)
SOMABRAIN_TAU_ANNEAL_RATE = env.float("SOMABRAIN_TAU_ANNEAL_RATE", default=0.0)
SOMABRAIN_TAU_ANNEAL_STEP_INTERVAL = env.int(
    "SOMABRAIN_TAU_ANNEAL_STEP_INTERVAL", default=0
)
SOMABRAIN_ENTROPY_CAP_ENABLED = env.bool("SOMABRAIN_ENTROPY_CAP_ENABLED", default=False)
SOMABRAIN_ENTROPY_CAP = env.float("SOMABRAIN_ENTROPY_CAP", default=0.0)
SOMABRAIN_ENABLE_ADVANCED_LEARNING = env.bool(
    "SOMABRAIN_ENABLE_ADVANCED_LEARNING", default=True
)
SOMABRAIN_LEARNING_RATE_DYNAMIC = env.bool(
    "SOMABRAIN_LEARNING_RATE_DYNAMIC", default=False
)

# Learning tenant configuration
SOMABRAIN_LEARNING_TENANTS_OVERRIDES = env.str(
    "SOMABRAIN_LEARNING_TENANTS_OVERRIDES", default=None
)
LEARNING_TENANTS_CONFIG = env.str("LEARNING_TENANTS_CONFIG", default=None)
SOMABRAIN_LEARNING_TENANTS_FILE = env.str(
    "SOMABRAIN_LEARNING_TENANTS_FILE", default=None
)

# Adaptation engine - (continuing in next chunk due to length limit...)
SOMABRAIN_ADAPT_LR = env.float("SOMABRAIN_ADAPT_LR", default=0.05)
SOMABRAIN_ADAPT_MAX_HISTORY = env.int("SOMABRAIN_ADAPT_MAX_HISTORY", default=1000)
SOMABRAIN_ADAPT_ALPHA_MIN = env.float("SOMABRAIN_ADAPT_ALPHA_MIN", default=0.1)
SOMABRAIN_ADAPT_ALPHA_MAX = env.float("SOMABRAIN_ADAPT_ALPHA_MAX", default=5.0)
SOMABRAIN_ADAPT_GAMMA_MIN = env.float("SOMABRAIN_ADAPT_GAMMA_MIN", default=0.0)
SOMABRAIN_ADAPT_GAMMA_MAX = env.float("SOMABRAIN_ADAPT_GAMMA_MAX", default=1.0)
SOMABRAIN_ADAPT_LAMBDA_MIN = env.float("SOMABRAIN_ADAPT_LAMBDA_MIN", default=0.1)
SOMABRAIN_ADAPT_LAMBDA_MAX = env.float("SOMABRAIN_ADAPT_LAMBDA_MAX", default=5.0)
SOMABRAIN_ADAPT_MU_MIN = env.float("SOMABRAIN_ADAPT_MU_MIN", default=0.01)
SOMABRAIN_ADAPT_MU_MAX = env.float("SOMABRAIN_ADAPT_MU_MAX", default=5.0)
SOMABRAIN_ADAPT_NU_MIN = env.float("SOMABRAIN_ADAPT_NU_MIN", default=0.01)
SOMABRAIN_ADAPT_NU_MAX = env.float("SOMABRAIN_ADAPT_NU_MAX", default=5.0)
SOMABRAIN_ADAPT_GAIN_ALPHA = env.float("SOMABRAIN_ADAPT_GAIN_ALPHA", default=1.0)
SOMABRAIN_ADAPT_GAIN_GAMMA = env.float("SOMABRAIN_ADAPT_GAIN_GAMMA", default=-0.5)
SOMABRAIN_ADAPT_GAIN_LAMBDA = env.float("SOMABRAIN_ADAPT_GAIN_LAMBDA", default=1.0)
SOMABRAIN_ADAPT_GAIN_MU = env.float("SOMABRAIN_ADAPT_GAIN_MU", default=-0.25)
SOMABRAIN_ADAPT_GAIN_NU = env.float("SOMABRAIN_ADAPT_GAIN_NU", default=-0.25)

# Utility weights
SOMABRAIN_UTILITY_LAMBDA = env.float("SOMABRAIN_UTILITY_LAMBDA", default=1.0)
SOMABRAIN_UTILITY_MU = env.float("SOMABRAIN_UTILITY_MU", default=0.1)
SOMABRAIN_UTILITY_NU = env.float("SOMABRAIN_UTILITY_NU", default=0.05)
SOMABRAIN_UTILITY_LAMBDA_MIN = env.float("SOMABRAIN_UTILITY_LAMBDA_MIN", default=0.0)
SOMABRAIN_UTILITY_LAMBDA_MAX = env.float("SOMABRAIN_UTILITY_LAMBDA_MAX", default=5.0)
SOMABRAIN_UTILITY_MU_MIN = env.float("SOMABRAIN_UTILITY_MU_MIN", default=0.0)
SOMABRAIN_UTILITY_MU_MAX = env.float("SOMABRAIN_UTILITY_MU_MAX", default=5.0)
SOMABRAIN_UTILITY_NU_MIN = env.float("SOMABRAIN_UTILITY_NU_MIN", default=0.0)
SOMABRAIN_UTILITY_NU_MAX = env.float("SOMABRAIN_UTILITY_NU_MAX", default=5.0)

# Neuromodulator settings
SOMABRAIN_NEURO_DOPAMINE_BASE = env.float("SOMABRAIN_NEURO_DOPAMINE_BASE", default=0.4)
SOMABRAIN_NEURO_SEROTONIN_BASE = env.float(
    "SOMABRAIN_NEURO_SEROTONIN_BASE", default=0.5
)
SOMABRAIN_NEURO_NORAD_BASE = env.float("SOMABRAIN_NEURO_NORAD_BASE", default=0.0)
SOMABRAIN_NEURO_ACETYL_BASE = env.float("SOMABRAIN_NEURO_ACETYL_BASE", default=0.0)

# Neuromodulator Adaptive Bounds
SOMABRAIN_NEURO_DOPAMINE_MIN = env.float("SOMABRAIN_NEURO_DOPAMINE_MIN", default=0.2)
SOMABRAIN_NEURO_DOPAMINE_MAX = env.float("SOMABRAIN_NEURO_DOPAMINE_MAX", default=0.8)
SOMABRAIN_NEURO_DOPAMINE_LR = env.float("SOMABRAIN_NEURO_DOPAMINE_LR", default=0.01)

SOMABRAIN_NEURO_SEROTONIN_MIN = env.float("SOMABRAIN_NEURO_SEROTONIN_MIN", default=0.0)
SOMABRAIN_NEURO_SEROTONIN_MAX = env.float("SOMABRAIN_NEURO_SEROTONIN_MAX", default=1.0)
SOMABRAIN_NEURO_SEROTONIN_LR = env.float("SOMABRAIN_NEURO_SEROTONIN_LR", default=0.01)

SOMABRAIN_NEURO_NORAD_MIN = env.float("SOMABRAIN_NEURO_NORAD_MIN", default=0.0)
SOMABRAIN_NEURO_NORAD_MAX = env.float("SOMABRAIN_NEURO_NORAD_MAX", default=0.1)
SOMABRAIN_NEURO_NORAD_LR = env.float("SOMABRAIN_NEURO_NORAD_LR", default=0.01)

SOMABRAIN_NEURO_ACETYL_MIN = env.float("SOMABRAIN_NEURO_ACETYL_MIN", default=0.0)
SOMABRAIN_NEURO_ACETYL_MAX = env.float("SOMABRAIN_NEURO_ACETYL_MAX", default=0.1)
SOMABRAIN_NEURO_ACETYL_LR = env.float("SOMABRAIN_NEURO_ACETYL_LR", default=0.01)

# Neuromodulator Feedback Parameters
SOMABRAIN_NEURO_DOPAMINE_REWARD_BOOST = env.float(
    "SOMABRAIN_NEURO_DOPAMINE_REWARD_BOOST", default=0.1
)
SOMABRAIN_NEURO_DOPAMINE_BIAS = env.float("SOMABRAIN_NEURO_DOPAMINE_BIAS", default=0.05)
SOMABRAIN_NEURO_URGENCY_FACTOR = env.float(
    "SOMABRAIN_NEURO_URGENCY_FACTOR", default=0.02
)
SOMABRAIN_NEURO_LATENCY_FLOOR = env.float("SOMABRAIN_NEURO_LATENCY_FLOOR", default=0.1)
SOMABRAIN_NEURO_LATENCY_SCALE = env.float("SOMABRAIN_NEURO_LATENCY_SCALE", default=0.01)
SOMABRAIN_NEURO_MEMORY_FACTOR = env.float("SOMABRAIN_NEURO_MEMORY_FACTOR", default=0.02)
SOMABRAIN_NEURO_ACCURACY_SCALE = env.float(
    "SOMABRAIN_NEURO_ACCURACY_SCALE", default=0.05
)

# Sleep system
SOMABRAIN_ENABLE_SLEEP = env.bool("SOMABRAIN_ENABLE_SLEEP", default=True)
SOMABRAIN_CONSOLIDATION_ENABLED = env.bool(
    "SOMABRAIN_CONSOLIDATION_ENABLED", default=True
)
SOMABRAIN_SLEEP_INTERVAL_SECONDS = env.int(
    "SOMABRAIN_SLEEP_INTERVAL_SECONDS", default=3600
)
SOMABRAIN_CONSOLIDATION_TIMEOUT_S = env.float(
    "SOMABRAIN_CONSOLIDATION_TIMEOUT_S", default=30.0
)
SOMABRAIN_NREM_BATCH_SIZE = env.int("SOMABRAIN_NREM_BATCH_SIZE", default=16)
SOMABRAIN_MAX_SUMMARIES_PER_CYCLE = env.int(
    "SOMABRAIN_MAX_SUMMARIES_PER_CYCLE", default=3
)
SOMABRAIN_REM_RECOMB_RATE = env.float("SOMABRAIN_REM_RECOMB_RATE", default=0.2)

# Sleep parameters (detailed configuration)
SLEEP_K0 = env.int("SLEEP_K0", default=10)
SLEEP_T0 = env.float("SLEEP_T0", default=1.0)
SLEEP_TAU0 = env.float("SLEEP_TAU0", default=0.1)
SLEEP_ETA0 = env.float("SLEEP_ETA0", default=0.01)

# Learning & Adaptation Settings
SOMABRAIN_UTILITY_LAMBDA = env.float("SOMABRAIN_UTILITY_LAMBDA", default=1.0)
SOMABRAIN_UTILITY_MU = env.float("SOMABRAIN_UTILITY_MU", default=0.1)
SOMABRAIN_UTILITY_NU = env.float("SOMABRAIN_UTILITY_NU", default=0.05)
SOMABRAIN_ADAPTATION_GAIN_ALPHA = env.float(
    "SOMABRAIN_ADAPTATION_GAIN_ALPHA", default=1.0
)
SOMABRAIN_ADAPTATION_GAIN_GAMMA = env.float(
    "SOMABRAIN_ADAPTATION_GAIN_GAMMA", default=-0.5
)
SOMABRAIN_ADAPTATION_GAIN_LAMBDA = env.float(
    "SOMABRAIN_ADAPTATION_GAIN_LAMBDA", default=1.0
)
SOMABRAIN_ADAPTATION_GAIN_MU = env.float("SOMABRAIN_ADAPTATION_GAIN_MU", default=-0.25)
SOMABRAIN_ADAPTATION_GAIN_NU = env.float("SOMABRAIN_ADAPTATION_GAIN_NU", default=-0.25)
SOMABRAIN_ADAPTATION_ALPHA_MIN = env.float(
    "SOMABRAIN_ADAPTATION_ALPHA_MIN", default=0.1
)
SOMABRAIN_ADAPTATION_ALPHA_MAX = env.float(
    "SOMABRAIN_ADAPTATION_ALPHA_MAX", default=5.0
)
SOMABRAIN_ADAPTATION_GAMMA_MIN = env.float(
    "SOMABRAIN_ADAPTATION_GAMMA_MIN", default=0.0
)
SOMABRAIN_ADAPTATION_GAMMA_MAX = env.float(
    "SOMABRAIN_ADAPTATION_GAMMA_MAX", default=1.0
)
SOMABRAIN_ADAPTATION_LAMBDA_MIN = env.float(
    "SOMABRAIN_ADAPTATION_LAMBDA_MIN", default=0.1
)
SOMABRAIN_ADAPTATION_LAMBDA_MAX = env.float(
    "SOMABRAIN_ADAPTATION_LAMBDA_MAX", default=5.0
)
SOMABRAIN_ADAPTATION_MU_MIN = env.float("SOMABRAIN_ADAPTATION_MU_MIN", default=0.01)
SOMABRAIN_ADAPTATION_MU_MAX = env.float("SOMABRAIN_ADAPTATION_MU_MAX", default=5.0)
SOMABRAIN_ADAPTATION_NU_MIN = env.float("SOMABRAIN_ADAPTATION_NU_MIN", default=0.01)
SOMABRAIN_ADAPTATION_NU_MAX = env.float("SOMABRAIN_ADAPTATION_NU_MAX", default=5.0)
SLEEP_LAMBDA0 = env.float("SLEEP_LAMBDA0", default=0.5)
SLEEP_B0 = env.float("SLEEP_B0", default=1.0)
SLEEP_K_MIN = env.int("SLEEP_K_MIN", default=5)
SLEEP_T_MIN = env.float("SLEEP_T_MIN", default=0.5)
SLEEP_ALPHA_K = env.float("SLEEP_ALPHA_K", default=0.1)
SLEEP_ALPHA_T = env.float("SLEEP_ALPHA_T", default=0.05)
SLEEP_ALPHA_TAU = env.float("SLEEP_ALPHA_TAU", default=0.05)
SLEEP_ALPHA_ETA = env.float("SLEEP_ALPHA_ETA", default=0.01)
SLEEP_BETA_B = env.float("SLEEP_BETA_B", default=0.1)

# Predictor configuration
SOMABRAIN_PREDICTOR_PROVIDER = env.str("SOMABRAIN_PREDICTOR_PROVIDER", default="mahal")
SOMABRAIN_PREDICTOR_DIM = env.int("SOMABRAIN_PREDICTOR_DIM", default=16)
SOMABRAIN_PREDICTOR_ALPHA = env.float("SOMABRAIN_PREDICTOR_ALPHA", default=2.0)
SOMABRAIN_PREDICTOR_GAMMA = env.float("SOMABRAIN_PREDICTOR_GAMMA", default=-0.5)

# Lifecycle & Background Tasks
SOMABRAIN_OUTBOX_SYNC_INTERVAL = env.float(
    "SOMABRAIN_OUTBOX_SYNC_INTERVAL", default=10.0
)
SOMABRAIN_MILVUS_RECONCILE_INTERVAL = env.float(
    "SOMABRAIN_MILVUS_RECONCILE_INTERVAL", default=3600.0
)
SOMABRAIN_MEMORY_HEALTH_POLL_INTERVAL = env.int(
    "SOMABRAIN_MEMORY_HEALTH_POLL_INTERVAL", default=60
)
SOMABRAIN_MEMORY_FAST_ACK = env.bool("SOMABRAIN_MEMORY_FAST_ACK", default=False)

# Segmentation
SOMABRAIN_SEGMENT_GRAD_THRESH = env.float("SOMABRAIN_SEGMENT_GRAD_THRESH", default=0.2)
SOMABRAIN_SEGMENT_HMM_THRESH = env.float("SOMABRAIN_SEGMENT_HMM_THRESH", default=0.6)
SOMABRAIN_SEGMENTATION_HEALTH_PORT = env.int(
    "SOMABRAIN_SEGMENTATION_HEALTH_PORT", default=9016
)

# Drift monitoring
SOMABRAIN_DRIFT_STORE = env.str(
    "SOMABRAIN_DRIFT_STORE", default="./data/drift/state.json"
)

# LLM endpoint
SOMABRAIN_LLM_ENDPOINT = env.str("SOMABRAIN_LLM_ENDPOINT", default=None)

# --- OAK (ROAMDP) SETTINGS ---
ENABLE_OAK = env.bool("ENABLE_OAK", default=False)
OAK_BASE_UTILITY = env.float("OAK_BASE_UTILITY", default=1.0)
OAK_UTILITY_FACTOR = env.float("OAK_UTILITY_FACTOR", default=0.1)
OAK_TAU_MIN = env.float("OAK_TAU_MIN", default=30.0)
OAK_TAU_MAX = env.float("OAK_TAU_MAX", default=300.0)
OAK_PLAN_MAX_OPTIONS = env.int("OAK_PLAN_MAX_OPTIONS", default=10)
OAK_SIMILARITY_THRESHOLD = env.float("OAK_SIMILARITY_THRESHOLD", default=0.8)
OAK_REWARD_THRESHOLD = env.float("OAK_REWARD_THRESHOLD", default=0.5)
OAK_NOVELTY_THRESHOLD = env.float("OAK_NOVELTY_THRESHOLD", default=0.2)
OAK_GAMMA = env.float("OAK_GAMMA", default=0.99)
OAK_ALPHA = env.float("OAK_ALPHA", default=0.1)
OAK_KAPPA = env.float("OAK_KAPPA", default=1.0)

# --- COGNITIVE SETTINGS ---
# HRR configuration
SOMABRAIN_HRR_DIM = env.int("SOMABRAIN_HRR_DIM", default=8192)
SOMABRAIN_HRR_DTYPE = env.str("SOMABRAIN_HRR_DTYPE", default="float32")
SOMABRAIN_HRR_RENORM = env.bool("SOMABRAIN_HRR_RENORM", default=True)
SOMABRAIN_HRR_VECTOR_FAMILY = env.str("SOMABRAIN_HRR_VECTOR_FAMILY", default="bhdc")
SOMABRAIN_BHDC_SPARSITY = env.float("SOMABRAIN_BHDC_SPARSITY", default=0.1)

# SDR configuration
SOMABRAIN_SDR_BITS = env.int("SOMABRAIN_SDR_BITS", default=2048)
SOMABRAIN_SDR_DENSITY = env.float("SOMABRAIN_SDR_DENSITY", default=0.03)
SOMABRAIN_SDR_DIM = env.int("SOMABRAIN_SDR_DIM", default=16384)
SOMABRAIN_SDR_SPARSITY = env.float("SOMABRAIN_SDR_SPARSITY", default=0.01)

# Context configuration
SOMABRAIN_CONTEXT_BUDGET_TOKENS = env.int(
    "SOMABRAIN_CONTEXT_BUDGET_TOKENS", default=2048
)
SOMABRAIN_MAX_SUPERPOSE = env.int("SOMABRAIN_MAX_SUPERPOSE", default=32)
SOMABRAIN_DEFAULT_WM_SLOTS = env.int("SOMABRAIN_DEFAULT_WM_SLOTS", default=12)

# Determinism and seeding
SOMABRAIN_GLOBAL_SEED = env.int("SOMABRAIN_GLOBAL_SEED", default=42)
SOMABRAIN_DETERMINISM = env.bool("SOMABRAIN_DETERMINISM", default=True)

# Quotas
SOMABRAIN_QUOTA_TENANT = env.int("SOMABRAIN_QUOTA_TENANT", default=10000)
SOMABRAIN_QUOTA_TOOL = env.int("SOMABRAIN_QUOTA_TOOL", default=1000)
SOMABRAIN_QUOTA_ACTION = env.int("SOMABRAIN_QUOTA_ACTION", default=500)

# Quantum layer
SOMABRAIN_QUANTUM_DIM = env.int("SOMABRAIN_QUANTUM_DIM", default=2048)
SOMABRAIN_QUANTUM_SPARSITY = env.float("SOMABRAIN_QUANTUM_SPARSITY", default=0.1)

# Planning configuration
SOMABRAIN_USE_PLANNER = env.bool("SOMABRAIN_USE_PLANNER", default=False)
SOMABRAIN_USE_FOCUS_STATE = env.bool("SOMABRAIN_USE_FOCUS_STATE", default=True)
SOMABRAIN_PLAN_MAX_STEPS = env.int("SOMABRAIN_PLAN_MAX_STEPS", default=5)
SOMABRAIN_PLANNER_BACKEND = env.str("SOMABRAIN_PLANNER_BACKEND", default="bfs")

# ============================================================================
# DJANGO LOGGING CONFIGURATION - Console-only for Docker, file+console for local dev
# ============================================================================
# Check if log path is writable (Docker containers are read-only)
import os as _os

_log_file_writable = False
try:
    _log_dir = _os.path.dirname(SOMABRAIN_LOG_PATH) or "."
    if _os.path.exists(_log_dir) and _os.access(_log_dir, _os.W_OK):
        _log_file_writable = True
    elif not _os.path.exists(_log_dir):
        # Try to create - will fail on read-only filesystem
        try:
            _os.makedirs(_log_dir, exist_ok=True)
            _log_file_writable = True
        except OSError:
            pass
except Exception:
    pass

# Build handlers dict - only include 'file' if writable
_logging_handlers = {
    "console": {
        "level": SOMABRAIN_LOG_LEVEL,
        "class": "logging.StreamHandler",
        "formatter": "verbose",
    },
}
if _log_file_writable:
    _logging_handlers["file"] = {
        "level": "INFO",
        "class": "logging.FileHandler",
        "filename": SOMABRAIN_LOG_PATH,
        "formatter": "verbose",
    }

# Use console-only or console+file depending on writability
_active_handlers = ["console", "file"] if _log_file_writable else ["console"]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {module} {process:d} {thread:d} {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "filters": {
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
    },
    "handlers": _logging_handlers,
    "root": {
        "handlers": _active_handlers,
        "level": SOMABRAIN_LOG_LEVEL,
    },
    "loggers": {
        "django": {
            "handlers": _active_handlers,
            "level": SOMABRAIN_LOG_LEVEL,
            "propagate": False,
        },
        "somabrain": {
            "handlers": _active_handlers,
            "level": SOMABRAIN_LOG_LEVEL,
            "propagate": False,
        },
    },
}

# =============================================================================
# GOOGLE OAUTH SETTINGS (SSO)
# =============================================================================
GOOGLE_OAUTH_CLIENT_ID = env("GOOGLE_OAUTH_CLIENT_ID", default="")
GOOGLE_OAUTH_CLIENT_SECRET = env("GOOGLE_OAUTH_CLIENT_SECRET", default="")
GOOGLE_OAUTH_PROJECT_ID = env("GOOGLE_OAUTH_PROJECT_ID", default="")
GOOGLE_OAUTH_REDIRECT_URI = env(
    "GOOGLE_OAUTH_REDIRECT_URI", default="http://localhost:30173/auth/callback"
)

# =============================================================================
# KEYCLOAK SETTINGS (SSO)
# =============================================================================
KEYCLOAK_URL = env("KEYCLOAK_URL", default="http://localhost:8080")
KEYCLOAK_REALM = env("KEYCLOAK_REALM", default="somabrain")
KEYCLOAK_CLIENT_ID = env("KEYCLOAK_CLIENT_ID", default="somabrain-api")
KEYCLOAK_CLIENT_SECRET = env("KEYCLOAK_CLIENT_SECRET", default="")

# =============================================================================
# LAGO BILLING SETTINGS
# =============================================================================
LAGO_URL = env("LAGO_URL", default="http://localhost:3000")
LAGO_API_KEY = env("LAGO_API_KEY", default="")
LAGO_WEBHOOK_SECRET = env("LAGO_WEBHOOK_SECRET", default="")

# =============================================================================
# SOMAFRACTALMEMORY INTEGRATION
# =============================================================================
SOMAFRACTALMEMORY_URL = env("SOMAFRACTALMEMORY_URL", default="http://localhost:9595")
SOMAFRACTALMEMORY_API_TOKEN = env("SOMAFRACTALMEMORY_API_TOKEN", default="")

# =============================================================================
# DJANGO EMAIL SETTINGS
# =============================================================================
# Backend: Use 'console' for development, 'smtp' for production
EMAIL_BACKEND = env(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)

# SMTP Configuration (for production)
EMAIL_HOST = env("EMAIL_HOST", default="smtp.gmail.com")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")

# Default sender
DEFAULT_FROM_EMAIL = env(
    "DEFAULT_FROM_EMAIL", default="SomaBrain <noreply@somabrain.ai>"
)
SERVER_EMAIL = env("SERVER_EMAIL", default="server@somabrain.ai")

# Email subject prefix (for admin emails)
EMAIL_SUBJECT_PREFIX = "[SomaBrain] "
