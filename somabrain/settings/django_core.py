
import environ
from pathlib import Path

env = environ.Env()

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ============================================================================
# DJANGO CORE APPLICATION SETTINGS
# ============================================================================

# Initialize django-environ
env = environ.Env(
    # Django core settings
    DEBUG=(bool, False),
    SECRET_KEY=(str, "django-insecure-change-me-locally-somabrain"),
    ALLOWED_HOSTS=(list, ["*"]),
    # SomaBrain core settings with defaults
    SOMABRAIN_LOG_LEVEL=(str, "INFO"),
    SOMABRAIN_POSTGRES_DSN=(str, ""),
    SOMABRAIN_API_URL=(str, "http://localhost:30101"),
    # Deployment Mode Standardization
    SOMA_DEPLOY_MODE=(str, "FULL_LOCAL"),
    SOMABRAIN_MODE=(str, "full-local"), # Legacy fallback
    SOMABRAIN_MEMORY_HTTP_ENDPOINT=(str, "http://localhost:10101"),
    SOMABRAIN_MEMORY_HTTP_TOKEN=(str, "test-token-123"),
    SOMABRAIN_CIRCUIT_FAILURE_THRESHOLD=(int, 5),
    SOMABRAIN_CIRCUIT_RESET_INTERVAL=(float, 30.0),
    SOMABRAIN_CIRCUIT_COOLDOWN_INTERVAL=(float, 60.0),
    SOMABRAIN_BHDC_SPARSITY=(float, 0.1),
    SOMABRAIN_WM_ALPHA=(float, 0.5),
    SOMABRAIN_WM_BETA=(float, 0.2),
    SOMABRAIN_WM_GAMMA=(float, 0.3),
    SOMABRAIN_WM_RECENCY_TIME_SCALE=(float, 60.0),
    SOMABRAIN_WM_RECENCY_MAX_STEPS=(float, 10.0),
    SOMABRAIN_WM_SALIENCE_THRESHOLD=(float, 0.6),
)

SOMABRAIN_API_URL = env("SOMABRAIN_API_URL")
SOMA_DEPLOY_MODE = env("SOMA_DEPLOY_MODE", default=env("SOMABRAIN_MODE"))
SOMABRAIN_MODE = SOMA_DEPLOY_MODE # Backward compatibility
SOMABRAIN_MEMORY_HTTP_ENDPOINT = env("SOMABRAIN_MEMORY_HTTP_ENDPOINT")
SOMABRAIN_MEMORY_HTTP_TOKEN = env("SOMABRAIN_MEMORY_HTTP_TOKEN")
SOMABRAIN_CIRCUIT_FAILURE_THRESHOLD = env("SOMABRAIN_CIRCUIT_FAILURE_THRESHOLD")
SOMABRAIN_CIRCUIT_RESET_INTERVAL = env("SOMABRAIN_CIRCUIT_RESET_INTERVAL")
SOMABRAIN_CIRCUIT_COOLDOWN_INTERVAL = env("SOMABRAIN_CIRCUIT_COOLDOWN_INTERVAL", default=60.0)
SOMABRAIN_BHDC_SPARSITY = env("SOMABRAIN_BHDC_SPARSITY", default=0.1)

# Working Memory Settings - Vibe Tuneable
SOMABRAIN_WM_ALPHA = env("SOMABRAIN_WM_ALPHA")
SOMABRAIN_WM_BETA = env("SOMABRAIN_WM_BETA")
SOMABRAIN_WM_GAMMA = env("SOMABRAIN_WM_GAMMA")
SOMABRAIN_WM_RECENCY_TIME_SCALE = env("SOMABRAIN_WM_RECENCY_TIME_SCALE")
SOMABRAIN_WM_RECENCY_MAX_STEPS = env("SOMABRAIN_WM_RECENCY_MAX_STEPS")
SOMABRAIN_WM_SALIENCE_THRESHOLD = env("SOMABRAIN_WM_SALIENCE_THRESHOLD")

# API Authentication Token
# Standardized to support SOMA_API_TOKEN or SOMA_API_TOKEN_FILE via environ's support
SOMA_API_TOKEN = env.str("SOMA_API_TOKEN", default=None)
SOMA_API_TOKEN_FILE = env.str("SOMA_API_TOKEN_FILE", default=None)

# Vault Integration for Secrets
try:
    from somabrain.core.security.vault_client import get_jwt_secret, VaultNotConfigured
    try:
        # Prioritize Vault for the Critical Secret
        _vault_secret = get_jwt_secret()
        if _vault_secret:
            os.environ["SOMABRAIN_JWT_SECRET"] = _vault_secret
            os.environ["SECRET_KEY"] = _vault_secret
    except (VaultNotConfigured, ImportError):
        pass
except ImportError:
    pass

SECRET_KEY = env("SOMABRAIN_JWT_SECRET", default=env("SECRET_KEY"))
DEBUG = env("SOMABRAIN_LOG_LEVEL") == "DEBUG"
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "somabrain",  # Main app
    "somabrain.aaas",  # AAAS: tenants, subscriptions, API keys
    "somabrain.brain_settings",  # GMD MathCore settings
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
]

ROOT_URLCONF = "somabrain.config.urls"

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

WSGI_APPLICATION = "somabrain.config.wsgi.application"
ASGI_APPLICATION = "somabrain.config.asgi.application"

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

# -----------------------------------------------------------------------------
# Helper function to load API token (matches existing logic)
# -----------------------------------------------------------------------------
def get_api_token() -> str | None:
    """Load the API token from settings or file."""
    if SOMA_API_TOKEN:
        return SOMA_API_TOKEN

    if SOMA_API_TOKEN_FILE:
        try:
            p = Path(SOMA_API_TOKEN_FILE)
            if p.exists():
                return p.read_text(encoding="utf-8").strip()
        except Exception:
            pass

    return None

# ============================================================================
# DJANGO LOGGING CONFIGURATION
# ============================================================================
SOMABRAIN_LOG_LEVEL = env.str("SOMABRAIN_LOG_LEVEL", default="INFO")
SOMABRAIN_LOG_PATH = env.str("SOMABRAIN_LOG_PATH", default="/app/logs/somabrain.log")

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
        "level": SOMABRAIN_LOG_LEVEL,
        "class": "logging.FileHandler",
        "filename": SOMABRAIN_LOG_PATH,
        "formatter": "verbose",
    }

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
    "handlers": _logging_handlers,
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
        "somabrain": {
            "handlers": list(_logging_handlers.keys()),
            "level": SOMABRAIN_LOG_LEVEL,
            "propagate": False,
        },
    },
}
