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
from .hit_processing import (
    normalize_recall_hits,
    hit_identity,
    hit_score,
    hit_timestamp,
    coerce_timestamp_value,
    prefer_candidate_hit,
    deduplicate_hits,
    lexical_bonus,
)
from .scoring import (
    coerce_float,
    parse_payload_timestamp,
    get_recency_normalisation,
    get_recency_profile,
    compute_recency_features,
    compute_density_factor,
    extract_cleanup_margin,
    rank_hits,
    apply_weighting_to_hits,
    rescore_and_rank_hits,
)
from .payload import (
    enrich_payload,
    normalize_metadata,
    prepare_memory_payload,
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
]


def get_memory_client():
    """Lazy import of MemoryClient to avoid circular imports."""
    from somabrain.memory_client import MemoryClient

    return MemoryClient


def get_memory_http_transport():
    """Lazy import of MemoryHTTPTransport to avoid circular imports."""
    from somabrain.memory_client import MemoryHTTPTransport

    return MemoryHTTPTransport
