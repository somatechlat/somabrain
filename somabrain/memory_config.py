from __future__ import annotations
from common.config.settings import settings
from dataclasses import dataclass
from typing import Optional
from common.config.settings import settings

"""Configuration dataclass for the memory client/adapter.

The original code accessed many environment variables directly via the global
``settings`` singleton.  To decouple the client from that global state we expose
the values that the adapter actually needs via a small ``@dataclass``.  The
defaults match the historic behaviour of the project.
"""


def _bool_env(name: str, default: bool = False) -> bool:
    """Read a boolean env var – ``1``, ``true``, ``yes`` and ``on`` are truthy."""
    val = getattr(settings, name.lower(), None)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


def _int_env(name: str, default: int) -> int:
    try:
        return int(getattr(settings, name.lower(), str(default)))
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise


@dataclass(slots=True)
class MemoryConfig:
    """Typed configuration for the memory HTTP adapter.

    Only the fields required by the current adapter are listed.  Additional
    flags (e.g. weighting, fast‑ack) are included because they are read by the
    original ``MemoryClient`` implementation and may be needed by callers.
    """

    # Core endpoint & authentication
    memory_http_endpoint: str = settings.memory_http_endpoint
    memory_http_token: Optional[str] = settings.memory_http_token

    # HTTP client tuning knobs
    http_max_connections: int = getattr(settings, "http_max_connections", 64)
    http_keepalive_connections: int = getattr(settings, "http_keepalive_connections", 32)
    http_retries: int = getattr(settings, "http_retries", 1)

    # Misc behavioural flags used by the original client
    memory_fast_ack: bool = bool(getattr(settings, "memory_fast_ack", False))
    memory_enable_weighting: bool = bool(getattr(settings, "memory_enable_weighting", False))

    # Namespace/tenant – optional but useful for multi‑tenant deployments
    namespace: Optional[str] = getattr(settings, "namespace", None)

    # Additional optional settings can be added here without touching the
    # adapter logic.
