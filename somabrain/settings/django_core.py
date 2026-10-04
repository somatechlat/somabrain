"""Core Django settings shared by every SomaBrain deployment profile.

This module owns the framework-level settings that are common across local,
standalone, and production-style deployments. Deployment-specific modules
import this file first, then layer infrastructure and feature settings on top.
"""

import os
from pathlib import Path

import environ  # type: ignore[import-untyped]

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
    # No default secrets per VIBE rules. Vault bootstrap or env must supply them.
    SECRET_KEY=(str, ""),
    ALLOWED_HOSTS=(list, []),
    # SomaBrain core settings with defaults
    SOMABRAIN_LOG_LEVEL=(str, "INFO"),
    # No default DSN per VIBE rules. Vault bootstrap or env must supply it.
    SOMABRAIN_POSTGRES_DSN=(str, ""),
    # No localhost default: an invented 127.0.0.1 is a URL an operator cannot
    # change and a reviewer cannot see. Empty means unset; require_url raises.
    SOMABRAIN_API_URL=(str, ""),
    # Deployment Mode Standardization
    SOMA_DEPLOY_MODE=(str, "FULL_LOCAL"),
    SOMABRAIN_MODE=(str, "full-local"),  # Legacy fallback
    # Memory endpoint moved to infra.py
    # SOMABRAIN_MEMORY_HTTP_ENDPOINT=(str, "http://127.0.0.1:10101"),
    # SOMABRAIN_MEMORY_HTTP_TOKEN=(str, "<runtime supplied>"),
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
SOMABRAIN_MODE = SOMA_DEPLOY_MODE  # Backward compatibility alias
# Memory endpoint moved to infra.py for centralized connection management
# SOMABRAIN_MEMORY_HTTP_ENDPOINT = env("SOMABRAIN_MEMORY_HTTP_ENDPOINT")
# SOMABRAIN_MEMORY_HTTP_TOKEN = env("SOMABRAIN_MEMORY_HTTP_TOKEN")
SOMABRAIN_CIRCUIT_FAILURE_THRESHOLD = env("SOMABRAIN_CIRCUIT_FAILURE_THRESHOLD")
SOMABRAIN_CIRCUIT_RESET_INTERVAL = env("SOMABRAIN_CIRCUIT_RESET_INTERVAL")
SOMABRAIN_CIRCUIT_COOLDOWN_INTERVAL = env(
    "SOMABRAIN_CIRCUIT_COOLDOWN_INTERVAL", default=60.0
)
SOMABRAIN_BHDC_SPARSITY = env("SOMABRAIN_BHDC_SPARSITY", default=0.1)

# Working Memory Settings - Vibe Tuneable
SOMABRAIN_WM_ALPHA = env("SOMABRAIN_WM_ALPHA")
SOMABRAIN_WM_BETA = env("SOMABRAIN_WM_BETA")
SOMABRAIN_WM_GAMMA = env("SOMABRAIN_WM_GAMMA")
SOMABRAIN_WM_RECENCY_TIME_SCALE = env("SOMABRAIN_WM_RECENCY_TIME_SCALE")
SOMABRAIN_WM_RECENCY_MAX_STEPS = env("SOMABRAIN_WM_RECENCY_MAX_STEPS")
SOMABRAIN_WM_SALIENCE_THRESHOLD = env("SOMABRAIN_WM_SALIENCE_THRESHOLD")

# API Authentication Token — secret, Vault only (somabrain/runtime[api_token]).
# ENV never carries it. See get_api_token() below.
SOMA_API_TOKEN = None  # populated from Vault below
SOMA_API_TOKEN_FILE = None


# Bootstrap secrets resolved from Vault and held here. Rule 164: they are
# never written to ``os.environ``. A secret in the process environment is
# visible in ``ps``, in ``/proc/*/environ`` and in every crash dump.
_BOOTSTRAP: dict[str, str] = {}


def _boot_secret(name: str, value: object | None) -> None:
    """Hold a Vault-resolved bootstrap secret in this module only."""
    if value is None:
        return
    text = str(value).strip()
    if text:
        _BOOTSTRAP[name] = text


def configure_vault_secrets() -> None:
    """Resolve bootstrap secrets from Vault into module state.

    Standalone Docker boots with Vault enabled. The same settings module is
    imported in CI and local development where Vault may be absent. Absence
    of Vault does not license a fallback: the secrets stay absent and the
    features that need them fail closed (Rule 91).

    Call once during application startup (e.g. from ``wsgi.py`` or
    ``AppConfig.ready()``) before Django resolves derived settings.
    """
    try:
        from somabrain.core.security.vault_client import (
            SecretNotFound,
            VaultNotConfigured,
            get_db_credentials,
            get_jwt_secret,
            get_runtime_secret,
        )
    except ImportError:
        return

    try:
        db_creds = get_db_credentials()
        if db_creds:
            user = db_creds.get("username")
            password = db_creds.get("password")
            # Topology may live in Vault alongside the credential. There is no
            # invented host/port/dbname here: absent means the DSN is not built.
            host = db_creds.get("host")
            port = db_creds.get("port")
            name = db_creds.get("dbname")
            if user and password and host and port and name:
                _boot_secret(
                    "SOMABRAIN_POSTGRES_DSN",
                    f"postgresql://{user}:{password}@{host}:{port}/{name}",
                )
    except (SecretNotFound, VaultNotConfigured):
        pass

    try:
        vault_secret = get_jwt_secret()
        if vault_secret:
            _boot_secret("SOMABRAIN_JWT_SECRET", vault_secret)
            _boot_secret("SECRET_KEY", vault_secret)
    except (SecretNotFound, VaultNotConfigured):
        pass

    try:
        api_token = get_runtime_secret("api_token")
    except (SecretNotFound, VaultNotConfigured):
        api_token = None

    if api_token:
        _boot_secret("SOMA_API_TOKEN", api_token)
        _boot_secret("SOMABRAIN_API_TOKEN", api_token)


# Resolve bootstrap secrets from Vault BEFORE the assignments below read them.
# The previous order populated `_BOOTSTRAP` after this module was imported, so
# the SECRET_KEY assignment never saw the Vault value and fell through to ENV.
configure_vault_secrets()

# Secret: Vault only (somabrain/auth[jwt_secret]). ENV never carries it.
SECRET_KEY = _BOOTSTRAP.get("SECRET_KEY", "")
if not SECRET_KEY:
    raise environ.ImproperlyConfigured(
        "SECRET_KEY must be provisioned via Vault (somabrain/auth[jwt_secret]). "
        "A secret is never read from the environment and there is no default "
        "(Rule 164 / Rule 91)."
    )

DEBUG = env("SOMABRAIN_LOG_LEVEL") == "DEBUG"
# Required host allow-list. A defaulted list (or an empty one that Django treats
# as "allow the test client only") is a gate, not a convenience: the operator
# names the hosts this service is addressed by. RFC 1035 alias `somabrain`.
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=[])
if not ALLOWED_HOSTS:
    raise environ.ImproperlyConfigured(
        "ALLOWED_HOSTS is required configuration. Name the host aliases this "
        "service is addressed by (for standalone: somabrain). There is no "
        "default list (Rule 91)."
    )

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "somabrain",  # Main app
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
# The DSN carries a password, so it is Vault material (somabrain/database),
# assembled in configure_vault_secrets(). ENV never carries a DSN (Rule 164).
_dsn = _BOOTSTRAP.get("SOMABRAIN_POSTGRES_DSN", "")
if not _dsn:
    raise environ.ImproperlyConfigured(
        "SOMABRAIN_POSTGRES_DSN must be provisioned via Vault "
        "(somabrain/database). A DSN carries a password and is never read "
        "from the environment (Rule 164 / Rule 91)."
    )
DATABASES = {"default": env.db_url_config(_dsn)}

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
# Helper function to load API token
# -----------------------------------------------------------------------------
def get_api_token() -> str | None:
    """Return the API token resolved from Vault.

    Returns ``None`` only when Vault did not provision one — a deployment that
    deliberately runs without an API token. The token is never read from the
    environment and never from a file path named by ENV (Rule 164). A failed
    Vault read is not "no token": it is an infrastructure failure and raises.
    """
    token = _BOOTSTRAP.get("SOMA_API_TOKEN") or _BOOTSTRAP.get("SOMABRAIN_API_TOKEN")
    return token or None


SOMABRAIN_API_TOKEN = get_api_token()
SOMA_API_TOKEN = SOMABRAIN_API_TOKEN

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
