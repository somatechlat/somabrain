"""Memory plane utilities for SomaBrain.

This module provides:
- TieredMemory: Hierarchical memory with layer policies
- SuperposedTrace: Trace configuration for memory operations
- RecallHit: Normalized memory recall hit from the SFM service
- MemoryHTTPTransport: HTTP transport layer for memory service (lazy import)
- MemoryClient: Main client for memory operations (lazy import from memory_client)
"""

from .hierarchical import LayerPolicy, RecallContext, TieredMemory
from .superposed_trace import SuperposedTrace, TraceConfig
from .types import RecallHit

__all__ = [
    # Hierarchical memory
    "LayerPolicy",
    "RecallContext",
    "TieredMemory",
    # Superposed trace
    "SuperposedTrace",
    "TraceConfig",
    # Memory client types
    "RecallHit",
]


def get_memory_client():
    """Lazy import of MemoryClient to avoid circular imports."""
    from somabrain.memory_client import MemoryClient

    return MemoryClient


def get_memory_http_transport():
    """Lazy import of MemoryHTTPTransport to avoid circular imports."""
    from somabrain.memory_client import MemoryHTTPTransport

    return MemoryHTTPTransport
