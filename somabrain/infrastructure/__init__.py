"""Infrastructure **package** for SomaBrain.

Historically the project exposed a *module* ``somabrain.core.infrastructure_defs`` that
contained a collection of helper functions such as ``get_memory_http_endpoint``
and ``get_api_base_url``.  A later refactor introduced a **package** named
``somabrain.core.infrastructure_defs`` with an ``__init__`` that only provided
``get_redis_url``.  Import statements throughout the codebase (e.g.
``from somabrain.core.infrastructure_defs import get_memory_http_endpoint``) therefore
resolved to the package and failed with ``ImportError`` because the symbols were
no longer exported.

To restore compatibility while keeping the implementation in the original
``infrastructure.py`` module, this ``__init__`` now re‑exports the full public
API from that module.  This approach avoids code duplication and ensures any
future updates to the helper functions are automatically reflected here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

from django.conf import settings

# ---------------------------------------------------------------------------
# Helper implementations – duplicated from ``somabrain/infrastructure.py``
# ---------------------------------------------------------------------------


def _clean(value: Optional[str]) -> Optional[str]:
    """Execute clean.

    Args:
        value: The value.
    """

    if value is None:
        return None
    try:
        text = str(value).strip()
    except Exception:
        return None
    return text or None


def _first_non_empty(*values: Optional[str]) -> Optional[str]:
    """Execute first non empty."""

    for value in values:
        cleaned = _clean(value)
        if cleaned:
            return cleaned
    return None


def _from_settings(attr: str) -> Optional[str]:
    # Retrieve configuration from the centralized Settings singleton.
    """Execute from settings.

    Args:
        attr: The attr.
    """

    try:
        return _clean(getattr(settings, attr, None))
    except Exception:
        return None


def get_redis_url(default: Optional[str] = None) -> Optional[str]:
    """Return the Redis connection URL from environment or shared settings."""
    url = _first_non_empty(
        _from_settings("SOMABRAIN_REDIS_URL"),
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


@dataclass(frozen=True)
class MemoryEndpoint:
    """Memoryendpoint class implementation."""

    scheme: str
    host: str
    port: Optional[int]
    url: str


def resolve_memory_endpoint(default: Optional[str] = None) -> MemoryEndpoint:
    """Return the canonical memory endpoint (scheme/host/port/url)."""

    explicit = _first_non_empty(_from_settings("SOMABRAIN_MEMORY_HTTP_ENDPOINT"))
    if explicit:
        scheme, host, port = _parse_url(explicit)
        return MemoryEndpoint(
            scheme=scheme, host=host, port=port, url=explicit.rstrip("/")
        )

    host = _from_settings("memory_http_host")
    port = _from_settings("memory_http_port")
    scheme = _from_settings("memory_http_scheme") or "http"
    if host:
        built = f"{scheme}://{host}:{port}" if port else f"{scheme}://{host}"
        return MemoryEndpoint(
            scheme=scheme,
            host=host,
            port=int(port) if port else None,
            url=built.rstrip("/"),
        )

    if default:
        scheme, host, port = _parse_url(default)
        return MemoryEndpoint(
            scheme=scheme, host=host, port=port, url=default.rstrip("/")
        )

    raise RuntimeError("Memory HTTP endpoint is not configured")


def get_memory_http_endpoint(default: Optional[str] = None) -> Optional[str]:
    """Compatibility wrapper returning only the endpoint URL."""

    try:
        return resolve_memory_endpoint(default).url
    except RuntimeError:
        return default


def get_kafka_bootstrap(default: Optional[str] = None) -> Optional[str]:
    """Return the Kafka bootstrap server list."""
    bootstrap = _first_non_empty(
        _from_settings("KAFKA_BOOTSTRAP_SERVERS"),
        _from_settings("SOMABRAIN_KAFKA_BOOTSTRAP"),
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
        _from_settings("SOMABRAIN_OPA_URL"),
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
    """Return the primary SomaBrain API base URL."""
    url = _first_non_empty(
        settings.SOMABRAIN_API_URL,
        settings.SOMABRAIN_API_URL,
        settings.SOMABRAIN_API_URL,
    )
    if url:
        return url

    host = _first_non_empty(settings.SOMABRAIN_HOST, settings.SOMABRAIN_HOST)
    port = _first_non_empty(settings.SOMABRAIN_PORT, settings.SOMABRAIN_PORT)
    scheme = (
        _first_non_empty(
            settings.SOMABRAIN_API_SCHEME,
            settings.SOMABRAIN_API_SCHEME,
        )
        or "http"
    )
    if host and port:
        return f"{scheme}://{host}:{port}"
    return default


def get_postgres_dsn(default: Optional[str] = None) -> Optional[str]:
    """Return the Postgres DSN."""
    dsn = _first_non_empty(
        _from_settings("SOMABRAIN_POSTGRES_DSN"),
        settings.SOMABRAIN_POSTGRES_DSN,
        getattr(settings, "SOMABRAIN_DATABASE_URL", None),
    )
    if dsn:
        return dsn
    return default


def require(value: Optional[str], *, message: str) -> str:
    """Ensure a configuration value exists, raising a RuntimeError otherwise."""
    if value:
        return value
    raise RuntimeError(message)


def _parse_url(value: str) -> tuple[str, str, Optional[int]]:
    """Execute parse url.

    Args:
        value: The value.
    """

    parsed = urlparse(value if "://" in value else f"http://{value}")
    if not parsed.hostname:
        raise RuntimeError(f"Invalid memory endpoint: {value!r}")
    return parsed.scheme or "http", parsed.hostname, parsed.port


__all__ = [
    "MemoryEndpoint",
    "get_api_base_url",
    "get_kafka_bootstrap",
    "get_memory_http_endpoint",
    "get_opa_url",
    "resolve_memory_endpoint",
    "get_postgres_dsn",
    "get_redis_url",
    "require",
]
