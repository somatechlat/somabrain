"""Infrastructure **package** for SomaBrain.

Historically the project exposed a *module* ``somabrain.infrastructure`` that
contained a collection of helper functions such as ``get_memory_http_endpoint``
and ``get_api_base_url``.  A later refactor introduced a **package** named
``somabrain.infrastructure`` with an ``__init__`` that only provided
``get_redis_url``.  Import statements throughout the codebase (e.g.
``from somabrain.infrastructure import get_memory_http_endpoint``) therefore
resolved to the package and failed with ``ImportError`` because the symbols were
no longer exported.

To restore compatibility while keeping the implementation in the original
``infrastructure.py`` module, this ``__init__`` now re‑exports the full public
API from that module.  This approach avoids code duplication and ensures any
future updates to the helper functions are automatically reflected here.
"""

from __future__ import annotations

from common.config.settings import settings
from typing import Optional

# ---------------------------------------------------------------------------
# Helper implementations – duplicated from ``somabrain/infrastructure.py``
# ---------------------------------------------------------------------------


def _clean(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    try:
        text = str(value).strip()
    except Exception as exc: raise
        return None
    return text or None


def _first_non_empty(*values: Optional[str]) -> Optional[str]:
    for value in values:
        cleaned = _clean(value)
        if cleaned:
            return cleaned
    return None


def _from_settings(attr: str) -> Optional[str]:
    # Retrieve configuration from the centralized Settings singleton.
    try:
        return _clean(getattr(settings, attr, None))
    except Exception as exc: raise
        return None


def get_redis_url(default: Optional[str] = None) -> Optional[str]:
    """Return the Redis connection URL from environment or shared settings."""
    url = _first_non_empty(
        _from_settings("redis_url"),
    )
    if url:
        return url

    host = _from_settings("redis_host")
    port = _from_settings("redis_port")
    db = _from_settings("redis_db")
    if host and port:
        suffix = f"/{db}" if db else ""
        return f"redis://{host}:{port}{suffix}"
    return default


def get_memory_http_endpoint(default: Optional[str] = None) -> Optional[str]:
    """Return the configured Memory HTTP endpoint."""
    endpoint = _first_non_empty(
        _from_settings("memory_http_endpoint"),
    )
    if endpoint:
        return endpoint

    host = _from_settings("memory_http_host")
    port = _from_settings("memory_http_port")
    scheme = _from_settings("memory_http_scheme") or "http"
    if host and port:
        return f"{scheme}://{host}:{port}"
    return default


def get_kafka_bootstrap(default: Optional[str] = None) -> Optional[str]:
    """Return the Kafka bootstrap server list."""
    bootstrap = _first_non_empty(
        _from_settings("kafka_bootstrap_servers"),
        _from_settings("kafka_bootstrap"),
    )
    if bootstrap:
        return bootstrap

    host = _from_settings("kafka_host")
    port = _from_settings("kafka_port")
    scheme = _from_settings("kafka_scheme") or "kafka"
    if host and port:
        return f"{scheme}://{host}:{port}"
    return default


def get_opa_url(default: Optional[str] = None) -> Optional[str]:
    """Return the Open Policy Agent endpoint."""
    url = _first_non_empty(
        _from_settings("opa_url"),
    )
    if url:
        return url

    host = _from_settings("opa_host")
    port = _from_settings("opa_port")
    scheme = _from_settings("opa_scheme") or "http"
    if host and port:
        return f"{scheme}://{host}:{port}"
    return default


def get_api_base_url(default: Optional[str] = None) -> Optional[str]:
    """Return the primary SomaBrain API base URL.

    The original implementation attempted to read a non‑existent ``settings.api_url``
    attribute, which caused an ``AttributeError`` during the end‑to‑end smoke test.
    The API base URL is derived from the public host/port configuration fields
    that *do* exist in ``Settings`` (``public_host`` and ``public_port``) or can
    be overridden via the ``SOMABRAIN_API_URL`` environment variable.
    """
    # 1️⃣  Explicit override – developers can set SOMABRAIN_API_URL directly.
    url = _first_non_empty(
        _from_settings("api_url"),  # maps to SOMABRAIN_API_URL if present
        settings.public_host,
        settings.public_port,
    )
    if isinstance(url, str) and url.startswith("http"):
        # ``api_url`` was provided as a full URL – return it unchanged.
        return url

    # 2️⃣  Build from host/port fields.
    host = _first_non_empty(settings.public_host)
    port = _first_non_empty(settings.public_port)
    scheme = _first_non_empty(settings.api_scheme) or "http"
    if host and port:
        return f"{scheme}://{host}:{port}"
    return default


def get_postgres_dsn(default: Optional[str] = None) -> Optional[str]:
    """Return the Postgres DSN."""
    dsn = _first_non_empty(
        _from_settings("postgres_dsn"),
        settings.postgres_dsn,
        # Use Settings attribute instead of deprecated getenv
        getattr(settings, "database_url", None),
    )
    if dsn:
        return dsn
    return default


def require(value: Optional[str], *, message: str) -> str:
    """Ensure a configuration value exists, raising a RuntimeError otherwise."""
    if value:
        return value
    raise RuntimeError(message)


__all__ = [
    "get_api_base_url",
    "get_kafka_bootstrap",
    "get_memory_http_endpoint",
    "get_opa_url",
    "get_postgres_dsn",
    "get_redis_url",
    "require",
]
