"""Configuration dataclass for the memory client/adapter.

The original code accessed many environment variables directly via the global
``settings`` singleton.  To decouple the client from that global state we expose
the values that the adapter actually needs via a small ``@dataclass``.  The
defaults match the historic behaviour of the project.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


def _bool_env(name: str, default: bool = False) -> bool:
    """Read a boolean env var – ``1``, ``true``, ``yes`` and ``on`` are truthy."""
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception as exc: raise
        return default


@dataclass(slots=True)
class MemoryConfig:
    """Typed configuration for the memory HTTP adapter.

    Only the fields required by the current adapter are listed.  Additional
    flags (e.g. weighting, fast‑ack) are included because they are read by the
    original ``MemoryClient`` implementation and may be needed by callers.
    """

    # Core endpoint & authentication
    memory_http_endpoint: str = os.getenv(
        "SOMABRAIN_MEMORY_HTTP_ENDPOINT", "http://localhost:9595"
    )
    memory_http_token: Optional[str] = os.getenv("SOMABRAIN_MEMORY_HTTP_TOKEN")

    # HTTP client tuning knobs
    http_max_connections: int = _int_env("SOMABRAIN_HTTP_MAX_CONNECTIONS", 64)
    http_keepalive_connections: int = _int_env("SOMABRAIN_HTTP_KEEPALIVE_CONNECTIONS", 32)
    http_retries: int = _int_env("SOMABRAIN_HTTP_RETRIES", 1)

    # Misc behavioural flags used by the original client
    memory_fast_ack: bool = _bool_env("SOMABRAIN_MEMORY_FAST_ACK", False)
    memory_enable_weighting: bool = _bool_env("SOMABRAIN_MEMORY_ENABLE_WEIGHTING", False)

    # Namespace/tenant – optional but useful for multi‑tenant deployments
    namespace: Optional[str] = os.getenv("SOMABRAIN_NAMESPACE")

    # Additional optional settings can be added here without touching the
    # adapter logic.
