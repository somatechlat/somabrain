"""Central helpers for service endpoints and infrastructure configuration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

try:
    # Shared settings loader; optional in some runtimes.
    from django.conf import settings

    # The Settings singleton is imported above; no need for a redundant alias.
except Exception:  # pragma: no cover - optional dependency in lean environments
    settings = None


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
    """Execute from settings.

    Args:
        attr: The attr.
    """

    if settings is None:
        return None
    try:
        return _clean(getattr(settings, attr, None))
    except Exception:
        return None


def get_redis_url(default: Optional[str] = None) -> Optional[str]:
    """Return the Redis connection URL from environment or shared settings."""

    url = _first_non_empty(
        _from_settings("SOMABRAIN_REDIS_URL"),
        # Settings provides redis_host, redis_port, redis_db as fallbacks
        _from_settings("SOMABRAIN_REDIS_HOST"),
        _from_settings("SOMABRAIN_REDIS_PORT"),
        _from_settings("SOMABRAIN_REDIS_DB"),
    )
    if url:
        return url

    host = _from_settings("SOMABRAIN_REDIS_HOST")
    port = _from_settings("SOMABRAIN_REDIS_PORT")
    db = _from_settings("SOMABRAIN_REDIS_DB")

    if host and port:
        suffix = f"/{db}" if db else ""
        return f"redis://{host}:{port}{suffix}"

    return default


@dataclass(frozen=True)
class MemoryEndpoint:
    """Normalized view of the memory HTTP endpoint configuration."""

    scheme: str
    host: str
    port: Optional[int]
    url: str


def resolve_memory_endpoint(default: Optional[str] = None) -> MemoryEndpoint:
    """Return the canonical memory endpoint configuration.

    The resolver prefers explicit URLs (``memory_http_endpoint``) but can also
    reconstruct a URL from ``memory_http_host``/``memory_http_port``. The result
    is cached implicitly via the ``settings`` singleton, so callers should not
    mutate the returned dataclass.
    """

    explicit = _first_non_empty(_from_settings("SOMABRAIN_MEMORY_HTTP_ENDPOINT"))
    if explicit:
        clean = explicit.rstrip("/")
        scheme, host, port = _parse_url(clean)
        return MemoryEndpoint(scheme=scheme, host=host, port=port, url=clean)

    host = _from_settings("SOMABRAIN_MEMORY_HTTP_HOST")
    port = _from_settings("SOMABRAIN_MEMORY_HTTP_PORT")
    scheme = _from_settings("SOMABRAIN_MEMORY_HTTP_SCHEME") or "http"

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
    """Compatibility wrapper returning the resolved memory endpoint URL."""

    try:
        return resolve_memory_endpoint(default).url
    except RuntimeError:
        return default


def _parse_url(value: str) -> tuple[str, str, Optional[int]]:
    """Parse *value* into ``(scheme, host, port)`` with basic validation."""

    from urllib.parse import urlparse

    parsed = urlparse(value if "://" in value else f"http://{value}")
    if not parsed.hostname:
        raise RuntimeError(f"Invalid memory endpoint: {value!r}")
    port = parsed.port
    return parsed.scheme or "http", parsed.hostname, port


def get_kafka_bootstrap(default: Optional[str] = None) -> Optional[str]:
    """Return the Kafka bootstrap server list."""

    bootstrap = _first_non_empty(
        _from_settings("KAFKA_BOOTSTRAP_SERVERS"),
        # Settings may provide host/port/scheme as fallbacks
        _from_settings("SOMABRAIN_KAFKA_HOST"),
        _from_settings("SOMABRAIN_KAFKA_PORT"),
        _from_settings("SOMABRAIN_KAFKA_SCHEME"),
    )
    if bootstrap:
        return bootstrap

    host = _from_settings("SOMABRAIN_KAFKA_HOST")
    port = _from_settings("SOMABRAIN_KAFKA_PORT")
    scheme = _from_settings("SOMABRAIN_KAFKA_SCHEME") or "kafka"

    if host and port:
        return f"{scheme}://{host}:{port}"

    return default


def get_opa_url(default: Optional[str] = None) -> Optional[str]:
    """Return the Open Policy Agent endpoint."""

    url = _first_non_empty(
        _from_settings("SOMABRAIN_OPA_URL"),
        # Settings fallbacks via host/port/scheme
        _from_settings("SOMABRAIN_OPA_HOST"),
        _from_settings("SOMABRAIN_OPA_PORT"),
        _from_settings("SOMABRAIN_OPA_SCHEME"),
    )
    if url:
        return url

    host = _from_settings("SOMABRAIN_OPA_HOST")
    port = _from_settings("SOMABRAIN_OPA_PORT")
    scheme = _from_settings("SOMABRAIN_OPA_SCHEME") or "http"

    if host and port:
        return f"{scheme}://{host}:{port}"

    return default


def get_api_base_url(default: Optional[str] = None) -> Optional[str]:
    """Return the primary SomaBrain API base URL."""

    url = _first_non_empty(
        _from_settings("SOMABRAIN_API_URL"),
        # Settings fallbacks via host/port/scheme
        _from_settings("SOMABRAIN_HOST"),
        _from_settings("SOMABRAIN_PORT"),
        _from_settings("SOMABRAIN_API_SCHEME"),
    )
    if url:
        return url

    host = _from_settings("SOMABRAIN_HOST")
    port = _from_settings("SOMABRAIN_PORT")
    scheme = _from_settings("SOMABRAIN_API_SCHEME") or "http"

    if host and port:
        return f"{scheme}://{host}:{port}"

    return default


def get_postgres_dsn(default: Optional[str] = None) -> Optional[str]:
    """Return the Postgres DSN."""

    dsn = _first_non_empty(
        _from_settings("SOMABRAIN_POSTGRES_DSN"),
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
