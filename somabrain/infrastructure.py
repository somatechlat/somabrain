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
        os.getenv("SOMABRAIN_REDIS_URL"),
        os.getenv("REDIS_URL"),
    )
    if url:
        return url

    host = _first_non_empty(
        os.getenv("SOMABRAIN_REDIS_HOST"),
        os.getenv("REDIS_HOST"),
    )
    port = _first_non_empty(
        os.getenv("SOMABRAIN_REDIS_PORT"),
        os.getenv("REDIS_PORT"),
    )
    db = _first_non_empty(
        os.getenv("SOMABRAIN_REDIS_DB"),
        os.getenv("REDIS_DB"),
    )

    if host and port:
        suffix = f"/{db}" if db else ""
        return f"redis://{host}:{port}{suffix}"

    return default


def get_memory_http_endpoint(default: Optional[str] = None) -> Optional[str]:
    """Return the configured Memory HTTP endpoint."""

    endpoint = _first_non_empty(
        _from_settings("memory_http_endpoint"),
        os.getenv("SOMABRAIN_MEMORY_HTTP_ENDPOINT"),
        os.getenv("SOMABRAIN_HTTP_ENDPOINT"),
        os.getenv("MEMORY_SERVICE_URL"),
    )
    if endpoint:
        return endpoint

    host = _first_non_empty(
        os.getenv("SOMABRAIN_MEMORY_HTTP_HOST"),
        os.getenv("MEMORY_HTTP_HOST"),
    )
    port = _first_non_empty(
        os.getenv("SOMABRAIN_MEMORY_HTTP_PORT"),
        os.getenv("MEMORY_HTTP_PORT"),
    )
    scheme = (
        _first_non_empty(
            os.getenv("SOMABRAIN_MEMORY_HTTP_SCHEME"),
            os.getenv("MEMORY_HTTP_SCHEME"),
        )
        or "http"
    )

    if host and port:
        return f"{scheme}://{host}:{port}"

    return default


def get_kafka_bootstrap(default: Optional[str] = None) -> Optional[str]:
    """Return the Kafka bootstrap server list."""

    bootstrap = _first_non_empty(
        _from_settings("kafka_bootstrap_servers"),
        os.getenv("SOMABRAIN_KAFKA_BOOTSTRAP"),
        os.getenv("SOMABRAIN_KAFKA_URL"),
        os.getenv("KAFKA_BOOTSTRAP_SERVERS"),
    )
    if bootstrap:
        return bootstrap

    host = _first_non_empty(
        os.getenv("SOMABRAIN_KAFKA_HOST"),
        os.getenv("KAFKA_HOST"),
    )
    port = _first_non_empty(
        os.getenv("SOMABRAIN_KAFKA_PORT"),
        os.getenv("KAFKA_PORT"),
    )
    scheme = (
        _first_non_empty(
            os.getenv("SOMABRAIN_KAFKA_SCHEME"),
            os.getenv("KAFKA_SCHEME"),
        )
        or "kafka"
    )

    if host and port:
        return f"{scheme}://{host}:{port}"

    return default


def get_opa_url(default: Optional[str] = None) -> Optional[str]:
    """Return the Open Policy Agent endpoint."""

    url = _first_non_empty(
        _from_settings("opa_url"),
        os.getenv("SOMABRAIN_OPA_URL"),
        os.getenv("SOMA_OPA_URL"),
    )
    if url:
        return url

    host = _first_non_empty(
        os.getenv("SOMABRAIN_OPA_HOST"),
        os.getenv("OPA_HOST"),
    )
    port = _first_non_empty(
        os.getenv("SOMABRAIN_OPA_PORT"),
        os.getenv("OPA_PORT"),
    )
    scheme = (
        _first_non_empty(
            os.getenv("SOMABRAIN_OPA_SCHEME"),
            os.getenv("OPA_SCHEME"),
        )
        or "http"
    )

    if host and port:
        return f"{scheme}://{host}:{port}"

    return default


def get_api_base_url(default: Optional[str] = None) -> Optional[str]:
    """Return the primary SomaBrain API base URL."""

    url = _first_non_empty(
        os.getenv("SOMABRAIN_API_URL"),
        os.getenv("SOMA_API_URL"),
        os.getenv("TEST_SERVER_URL"),
    )
    if url:
        return url

    host = _first_non_empty(
        os.getenv("SOMABRAIN_PUBLIC_HOST"),
        os.getenv("SOMABRAIN_HOST"),
    )
    port = _first_non_empty(
        os.getenv("SOMABRAIN_PUBLIC_PORT"),
        os.getenv("SOMABRAIN_HOST_PORT"),
    )
    scheme = (
        _first_non_empty(
            os.getenv("SOMABRAIN_API_SCHEME"),
            os.getenv("API_SCHEME"),
        )
        or "http"
    )

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
