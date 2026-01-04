"""Utility subpackage for shared helpers.

This package exposes shared helpers used by the consolidated architecture.

Exports:
* ``RedisCache`` – a thin Redis-backed TTL cache used by services.
* ``EtcdClient`` – minimal Etcd wrapper for feature-flag storage.
* ``AuthClient`` – HTTP client for the shared Auth service.
* ``configure_tracing`` / ``get_tracer`` – OpenTelemetry bootstrap helpers.

Having an ``__init__`` file makes ``import common.utils`` work on all Python
versions.
"""

from .auth_client import AuthClient
from .cache import RedisCache
from .etcd_client import EtcdClient
from .trace import configure_tracing, get_tracer

__all__ = [
    "AuthClient",
    "RedisCache",
    "EtcdClient",
    "configure_tracing",
    "get_tracer",
]