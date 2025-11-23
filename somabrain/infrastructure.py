"""Central helpers for service endpoints and infrastructure configuration."""

from __future__ import annotations

import os
from typing import Optional

try:
    # Shared settings loader; optional in some runtimes.
    from common.config.settings import settings
    shared_settings = settings  # type: ignore
except Exception:  # pragma: no cover - optional dependency in lean environments
    shared_settings = None  # type: ignore


def _clean(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    try:
        text = str(value).strip()
    except Exception:
        return None
    return text or None


def _first_non_empty(*values: Optional[str]) -> Optional[str]:
    for value in values:
        cleaned = _clean(value)
        if cleaned:
            return cleaned
    return None


def _from_settings(attr: str) -> Optional[str]:
    if shared_settings is None:
        return None
    try:
        return _clean(getattr(shared_settings, attr, None))
    except Exception:
        return None


def get_redis_url(default: Optional[str] = None) -> Optional[str]:
    """Return the Redis connection URL from environment or shared settings."""

    url = _first_non_empty(
        _from_settings("redis_url"),
        # Settings provides redis_host, redis_port, redis_db as fallbacks
        _from_settings("redis_host"),
        _from_settings("redis_port"),
        _from_settings("redis_db"),
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
        # fallbacks via Settings fields
        _from_settings("memory_http_host"),
        _from_settings("memory_http_port"),
        _from_settings("memory_http_scheme"),
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
        # Settings may provide host/port/scheme as fallbacks
        _from_settings("kafka_host"),
        _from_settings("kafka_port"),
        _from_settings("kafka_scheme"),
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
        # Settings fallbacks via host/port/scheme
        _from_settings("opa_host"),
        _from_settings("opa_port"),
        _from_settings("opa_scheme"),
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
        _from_settings("api_url"),
        # Settings fallbacks via host/port/scheme
        _from_settings("public_host"),
        _from_settings("public_port"),
        _from_settings("api_scheme"),
    )
    if url:
        return url

    host = _from_settings("public_host")
    port = _from_settings("public_port")
    scheme = _from_settings("api_scheme") or "http"

    if host and port:
        return f"{scheme}://{host}:{port}"

    return default


def get_postgres_dsn(default: Optional[str] = None) -> Optional[str]:
    """Return the Postgres DSN."""

    dsn = _first_non_empty(
        _from_settings("postgres_dsn"),
        os.getenv("SOMABRAIN_POSTGRES_DSN"),
        os.getenv("DATABASE_URL"),
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
