"""Memory Backend Factory - AAAS Mode Support.

Provides a factory function to get the appropriate memory backend based on
the SOMABRAIN_MEMORY_MODE environment variable.

AAAS = Agent As A Service mode.

Usage:
    from somabrain.memory.backends import get_memory_backend

    # Automatically selects HTTP or Direct based on SOMABRAIN_MEMORY_MODE
    backend = get_memory_backend(namespace="my_namespace")

    # Use the backend (same interface regardless of mode)
    backend.remember("key", {"data": "value"})
    results = backend.recall("search query")

Modes:
    - "http" (default): Uses MemoryClient for HTTP-based access
    - "direct": Uses DirectMemoryBackend for in-process access (AAAS mode)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from somabrain.interfaces.memory import MemoryBackend

logger = logging.getLogger(__name__)


def get_memory_backend(
    cfg: Optional[Any] = None,
    namespace: str = "default",
    tenant: str = "default",
) -> "MemoryBackend":
    """Factory function to get the appropriate memory backend.

    Reads SOMABRAIN_MEMORY_MODE from Django settings:
    - "http": Returns MemoryClient (HTTP backend)
    - "direct": Returns DirectMemoryBackend (AAAS mode)

    Args:
        cfg: Optional configuration object (for HTTP mode compatibility).
        namespace: The isolation namespace for memory operations.
        tenant: The tenant ID for multi-tenant isolation.

    Returns:
        MemoryBackend: The configured memory backend.

    Raises:
        ImportError: If "direct" mode is selected but somafractalmemory
            is not installed.
        ValueError: If an invalid mode is specified.

    Example:
        >>> backend = get_memory_backend(namespace="agents")
        >>> backend.remember("key1", {"task": "example"})
        >>> results = backend.recall("example")
    """
    from django.conf import settings as django_settings

    mode = getattr(django_settings, "SOMABRAIN_MEMORY_MODE", "http")
    logger.info(f"Creating memory backend in '{mode}' mode", extra={"namespace": namespace})

    if mode == "direct":
        try:
            from somabrain.memory.direct_backend import DirectMemoryBackend

            return DirectMemoryBackend(namespace=namespace, tenant=tenant)
        except ImportError as e:
            logger.exception("Failed to import DirectMemoryBackend")
            raise ImportError(
                "AAAS mode requires somafractalmemory. "
                "Install with: pip install somabrain[aaas]"
            ) from e

    elif mode == "http":
        # Default: HTTP mode
        from somabrain.memory_client import MemoryClient

        return MemoryClient(cfg)

    else:
        raise ValueError(
            f"Invalid SOMABRAIN_MEMORY_MODE: {mode}. "
            "Must be 'http' or 'direct'."
        )


def is_aaas_mode() -> bool:
    """Check if AAAS (direct) mode is enabled.

    Returns:
        True if SOMABRAIN_MEMORY_MODE is "direct", False otherwise.
    """
    from django.conf import settings as django_settings

    return getattr(django_settings, "SOMABRAIN_MEMORY_MODE", "http") == "direct"


def get_memory_mode() -> str:
    """Get the current memory backend mode.

    Returns:
        The current mode: "http" or "direct".
    """
    from django.conf import settings as django_settings

    return getattr(django_settings, "SOMABRAIN_MEMORY_MODE", "http")
