"""Core Django settings shared by every SomaBrain deployment profile.

This module owns the framework-level settings that are common across local,
standalone, and production-style deployments. Deployment-specific modules
import this file first, then layer infrastructure and feature settings on top.
"""

from pathlib import Path

import environ  # type: ignore[import-untyped]

env = environ.Env()

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ============================================================================
# DJANGO CORE APPLICATION SETTINGS
# ============================================================================

# Initialize django-environ.
# R-TOP: ENV is topology only. Behaviour knobs and secrets are NOT declared
# here — they are BrainSetting / Django settings (R-BEH-01) or Vault (R-SEC-01).
env = environ.Env(
    # No default secrets per VIBE rules. Vault bootstrap must supply them.
    SECRET_KEY=(str, ""),
    ALLOWED_HOSTS=(list, []),
    # No default DSN per VIBE rules. Vault bootstrap must supply it.
    SOMABRAIN_POSTGRES_DSN=(str, ""),
    # Deployment Mode Standardization (deployment topology, not a tunable)
    SOMA_DEPLOY_MODE=(str, "FULL_LOCAL"),
    SOMABRAIN_MODE=(str, "full-local"),  # Legacy fallback
)

SOMA_DEPLOY_MODE = env("SOMA_DEPLOY_MODE", default=env("SOMABRAIN_MODE"))
SOMABRAIN_MODE = SOMA_DEPLOY_MODE  # Backward compatibility alias

# --- Managed behaviour knobs (R-BEH-01: BrainSetting / Django, never ENV) ---
# Deployment URL. BrainSetting key ``api_url`` (TOPOLOGY). There is no ENV
# read and no invented host: runtime readers use managed_get("api_url") /
# require_url, which fail closed when the operator has not set it.
SOMABRAIN_API_URL = ""  # managed: BrainSetting api_url (no ENV)

# Circuit breaker. ONE declaration of the defaults (R-VAL-01). The
# administerable source is BrainSetting ``circuit_*`` (see BRAIN_DEFAULTS);
# these are the bootstrap values used before the DB is reachable. Read at the
# call site through require_setting / resolve_tunable / managed_get.
SOMABRAIN_CIRCUIT_FAILURE_THRESHOLD = 3
SOMABRAIN_CIRCUIT_RESET_INTERVAL = 60.0
SOMABRAIN_CIRCUIT_COOLDOWN_INTERVAL = 0.0

# BHDC sparsity is declared once in settings/cognitive.py (contracts.BHDC_P).
# DEF-01: django_core must not re-declare it — a star-import order would
# silently overwrite one of the two values.

# WM weight defaults (SOMABRAIN_WM_ALPHA/BETA/GAMMA/SALIENCE_THRESHOLD) are
# declared once in settings/cognitive.py.  DEF-01: django_core no longer
# re-declares them — base.py star-import order used to silently overwrite
# the cognitive defaults with different values.

# API Authentication Token — secret, Vault only (somabrain/runtime[api_token]).
# ENV never carries the value. See get_api_token() below.
# ``SOMA_API_TOKEN_FILE`` is a module-level credential-file slot (the same
# delivery shape as VAULT_TOKEN_FILE): a *path* is topology, the credential it
# names is not. Nothing in this module reads that path from ENV.
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
            VaultAuthError,
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
    except SecretNotFound:
        # Not provisioned: a deployment that deliberately runs without one.
        api_token = None
    except VaultAuthError:
        # Broken credential delivery is an infrastructure failure, not
        # "no token". It must never look like a deliberate unconfigured
        # deployment (Rule 91).
        raise
    except VaultNotConfigured:
        # Vault is not part of this environment at all. The token stays
        # absent and callers fail closed if they need one.
        api_token = None

    if api_token:
        _boot_secret("SOMA_API_TOKEN", api_token)


# Resolve bootstrap secrets from Vault BEFORE the assignments below read them.
# The previous order populated `_BOOTSTRAP` after this module was imported, so
# the SECRET_KEY assignment never saw the Vault value and fell through to ENV.
configure_vault_secrets()

# Hold the Vault-resolved API token in module state. get_api_token() reads
# these names (never ENV, never a silent default). SOMA_API_TOKEN is the
# inline credential; SOMA_API_TOKEN_FILE is the optional credential-file slot.
SOMA_API_TOKEN = _BOOTSTRAP.get("SOMA_API_TOKEN") or None

# Secret: Vault only (somabrain/auth[jwt_secret]). ENV never carries it.
SECRET_KEY = _BOOTSTRAP.get("SECRET_KEY", "")
if not SECRET_KEY:
    raise environ.ImproperlyConfigured(
        "SECRET_KEY must be provisioned via Vault (somabrain/auth[jwt_secret]). "
        "A secret is never read from the environment and there is no default "
        "(Rule 164 / Rule 91)."
    )

# F-02 CRITICAL: DEBUG is its own switch. It is NEVER derived from
# SOMABRAIN_LOG_LEVEL — log verbosity and Django debug behaviour are
# different concerns and coupling them turns "INFO logs" into "debug mode".
# Django settings are the source (R-BEH-01); deployment profiles pin it
# (production.py sets DEBUG = False). Not an ENV read.
DEBUG = False
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

# Production security posture, gated on the existing DEBUG flag above (whose
# computation is owned elsewhere and is not changed here). Mirrors
# somaAgent01/services/gateway/settings.py and the SFM twin in
# somafractalmemory/settings/django_core.py. Every switch below is the Django
# setting whose absence is the vulnerability: cookie theft over plain HTTP,
# MIME sniffing, clickjacking, and HSTS not being pinned. They are
# unconditional once DEBUG is off — an operator does not opt into them one by
# one.
if not DEBUG:
    # Cookie/header posture mirrors somaAgent01/services/gateway/settings.py.
    # SECURE_SSL_REDIRECT is intentionally NOT set: standalone and many
    # deployments terminate TLS at a proxy; forcing Django-level redirect
    # breaks plain-HTTP health checks and local compose. HSTS below still
    # pins browsers to TLS once a request has arrived over it.
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    CSRF_COOKIE_HTTPONLY = True
    # One year, includeSubDomains, preload — the same posture the gateway sets.
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"

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
    # Slim* skip session/CSRF/messages/session-auth **only** on /memory/* (Ninja
    # bearer API). OPA + Controls remain on every request. Browser routes keep
    # the full Django stack — see somabrain/controls/api_slim.py.
    "somabrain.controls.api_slim.SlimSessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "somabrain.controls.api_slim.SlimCsrfMiddleware",
    "somabrain.controls.api_slim.SlimAuthenticationMiddleware",
    "somabrain.controls.api_slim.SlimMessagesMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # OPA policy enforcement on every route (fail-closed in OpaMiddleware).
    "somabrain.controls.opa_middleware.OpaMiddleware",
    # Provenance / controls audit (REQUIRE_PROVENANCE, PROVENANCE_STRICT_DENY).
    "somabrain.controls.django_middleware.ControlsMiddleware",
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
# Connection pooling. Without CONN_MAX_AGE every request opens and closes a
# TCP connection to Postgres; CONN_HEALTH_CHECKS drops a connection that went
# stale while pooled so the first query after an idle window does not fail on
# a dead socket. Same values as somaAgent01/services/gateway/settings.py and
# somafractalmemory/settings/django_core.py.
DATABASES["default"]["CONN_MAX_AGE"] = 60
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

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
    """Return the API token from module state, or from its credential file.

    Resolution order:

    1. ``SOMA_API_TOKEN`` — module state, populated from Vault
       (``somabrain/runtime[api_token]``) by ``configure_vault_secrets``.
    2. ``SOMA_API_TOKEN_FILE`` — a path naming the credential file. The path
       is topology; the credential it names is not (same delivery shape as
       ``VAULT_TOKEN_FILE``). This function never reads ENV for either.

    Returns ``None`` only when nothing is configured — a deployment that
    deliberately runs without an API token. Any failure to *read* a named
    token file raises (Rule 91): "I could not read it" must never look like
    "it is not configured" (Rule 164 / Rule 91).
    """
    if SOMA_API_TOKEN:
        return SOMA_API_TOKEN

    if SOMA_API_TOKEN_FILE:
        token_path = Path(SOMA_API_TOKEN_FILE)
        try:
            resolved = token_path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise environ.ImproperlyConfigured(
                f"Cannot read the API token file named by SOMA_API_TOKEN_FILE "
                f"at {str(token_path)!r}: {exc.strerror or exc}. Fix the path "
                f"or the file's permissions; a failed read is not 'no token'."
            ) from None
        if not resolved:
            raise environ.ImproperlyConfigured(
                f"The API token file named by SOMA_API_TOKEN_FILE at "
                f"{str(token_path)!r} is empty. An empty credential is not "
                f"'no token configured'."
            )
        return resolved

    return None


# ONE canonical name (no dual keys): SOMA_API_TOKEN.
SOMA_API_TOKEN = get_api_token()

# ============================================================================
# DJANGO LOGGING CONFIGURATION
# ============================================================================
# Log level. BrainSetting key ``log_level`` (ops). NOT an ENV read, and it
# never drives DEBUG (F-02). One declaration here; LOGGING below consumes it.
# Runtime override: managed_get("log_level") / resolve_tunable("log_level").
SOMABRAIN_LOG_LEVEL = "INFO"
# Log file path is topology (a filesystem location), not a behaviour knob.
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
