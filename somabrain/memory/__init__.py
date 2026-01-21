"""Memory plane utilities for SomaBrain.

This module provides:
- TieredMemory: Hierarchical memory with layer policies
- SuperposedTrace: Trace configuration for memory operations
- RecallHit: Normalized memory recall hit from the SFM service
- MemoryHTTPTransport: HTTP transport layer for memory service
- MemoryClient: Main client for memory operations (lazy import from memory_client)
"""

from .filtering import _filter_payloads_by_keyword
from .hierarchical import LayerPolicy, RecallContext, TieredMemory
from .hit_processing import (
    coerce_timestamp_value,
    deduplicate_hits,
    hit_identity,
    hit_score,
    hit_timestamp,
    lexical_bonus,
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
from .normalization import _extract_memory_coord, _parse_coord_string, _stable_coord
from .payload import (
    enrich_payload,
    normalize_metadata,
    prepare_memory_payload,
)
from .recall_ops import (
    filter_hits_by_keyword,
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
from .scoring import (
    apply_weighting_to_hits,
    coerce_float,
    compute_density_factor,
    compute_recency_features,
    extract_cleanup_margin,
    get_recency_normalisation,
    get_recency_profile,
    parse_payload_timestamp,
    rank_hits,
    rescore_and_rank_hits,
)
from .superposed_trace import SuperposedTrace, TraceConfig
from .transport import MemoryHTTPTransport, _http_setting, _response_json
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
    "_http_setting",
    "_response_json",
    # Normalization
    "_stable_coord",
    "_parse_coord_string",
    "_extract_memory_coord",
    # Filtering
    "_filter_payloads_by_keyword",
    # Hit processing
    "normalize_recall_hits",
    "hit_identity",
    "hit_score",
    "hit_timestamp",
    "coerce_timestamp_value",
    "prefer_candidate_hit",
    "deduplicate_hits",
    "lexical_bonus",
    # Scoring
    "coerce_float",
    "parse_payload_timestamp",
    "get_recency_normalisation",
    "get_recency_profile",
    "compute_recency_features",
    "compute_density_factor",
    "extract_cleanup_margin",
    "rank_hits",
    "apply_weighting_to_hits",
    "rescore_and_rank_hits",
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
    "filter_hits_by_keyword",
    "process_search_response",
    # Utility functions
    "get_tenant_namespace",
    "coord_for_key",
    "fetch_by_coord",
    "store_from_payload",
]


def get_memory_client():
    """Lazy import of MemoryClient to avoid circular imports."""
    from somabrain.memory_client import MemoryClient

    return MemoryClient


def get_memory_http_transport():
    """Return MemoryHTTPTransport class (now directly imported)."""
    return MemoryHTTPTransport
