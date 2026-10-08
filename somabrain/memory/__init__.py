"""Memory plane utilities for SomaBrain.

This module provides:
- TieredMemory: Hierarchical memory with layer policies
- SuperposedTrace: Trace configuration for memory operations
- RecallHit: Normalized memory recall hit from the SFM service
- MemoryHTTPTransport: HTTP transport layer for memory service
- MemoryClient: Main client for memory operations
"""

from .client import MemoryClient
from .hierarchical import LayerPolicy, RecallContext, TieredMemory
from .client.ranking import lexical_bonus
from .hit_processing import (
    coerce_timestamp_value,
    deduplicate_hits,
    hit_identity,
    hit_score,
    hit_timestamp,
    normalize_recall_hits,
    prefer_candidate_hit,
)
from .http_helpers import (
    http_post_with_retries_async,
    http_post_with_retries_sync,
    record_http_metrics,
    store_bulk_http_async,
    store_bulk_http_sync,
    store_http_async,
    store_http_sync,
)
from .client.serialization import _stable_coord
from .normalization import _extract_memory_coord, _parse_coord_string
from .payload import (
    enrich_payload,
    normalize_metadata,
    prepare_memory_payload,
)
from .recall_ops import (
    memories_search_async,
    memories_search_sync,
    process_search_response,
)
from .remember import (
    aremember_background,
    prepare_bulk_items,
    process_bulk_response,
    remember_sync_persist,
)
from .superposed_trace import SuperposedTrace, TraceConfig
from .transport import MemoryHTTPTransport, _response_json
from .types import RecallHit
from .utils import (
    coord_for_key,
    fetch_by_coord,
    get_tenant_namespace,
    store_from_payload,
)

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
    # Transport
    "MemoryHTTPTransport",
    "_response_json",
    # Normalization
    "_stable_coord",
    "_parse_coord_string",
    "_extract_memory_coord",
    # Hit processing
    "normalize_recall_hits",
    "hit_identity",
    "hit_score",
    "hit_timestamp",
    "coerce_timestamp_value",
    "prefer_candidate_hit",
    "deduplicate_hits",
    "lexical_bonus",
    # Payload
    "enrich_payload",
    "normalize_metadata",
    "prepare_memory_payload",
    # HTTP helpers
    "record_http_metrics",
    "http_post_with_retries_sync",
    "http_post_with_retries_async",
    "store_http_sync",
    "store_http_async",
    "store_bulk_http_sync",
    "store_bulk_http_async",
    # Remember operations
    "remember_sync_persist",
    "aremember_background",
    "prepare_bulk_items",
    "process_bulk_response",
    # Recall operations
    "memories_search_sync",
    "memories_search_async",
    "process_search_response",
    # Utility functions
    "get_tenant_namespace",
    "coord_for_key",
    "fetch_by_coord",
    "store_from_payload",
]


def get_memory_client():
    """Return MemoryClient class (now directly imported)."""
    return MemoryClient


def get_memory_http_transport():
    """Return MemoryHTTPTransport class (now directly imported)."""
    return MemoryHTTPTransport
