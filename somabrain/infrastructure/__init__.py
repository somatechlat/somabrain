"""Infrastructure **package** for SomaBrain.

Single implementation lives in ``somabrain.core.infrastructure_defs``.
This package is a pure re-export so both import spellings resolve to the
same symbols (T-2 one definition — no duplicated bodies).
"""

from somabrain.core.infrastructure_defs import (
    MemoryEndpoint,
    get_api_base_url,
    get_kafka_bootstrap,
    get_memory_http_endpoint,
    get_opa_url,
    get_postgres_dsn,
    get_redis_url,
    require,
    resolve_memory_endpoint,
)

__all__ = [
    "MemoryEndpoint",
    "get_api_base_url",
    "get_kafka_bootstrap",
    "get_memory_http_endpoint",
    "get_opa_url",
    "get_postgres_dsn",
    "get_redis_url",
    "require",
    "resolve_memory_endpoint",
]
