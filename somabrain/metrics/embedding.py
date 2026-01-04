"""Embedding and Index Metrics for SomaBrain.

This module provides metrics for embedding operations, cache hits,
and index profile usage.

Metrics:
- EMBED_LAT: Histogram for embedding call latency by provider
- EMBED_CACHE_HIT: Counter for embedding cache hits
- INDEX_PROFILE_USE: Counter for index/compression profile usage
- LINK_DECAY_PRUNED: Counter for graph links pruned by decay
- AUDIT_KAFKA_PUBLISH: Counter for Kafka audit events
"""

from __future__ import annotations

from somabrain.metrics.core import Counter, Histogram, registry

# Embeddings
EMBED_LAT = Histogram(
    "somabrain_embed_latency_seconds",
    "Embedding call latency",
    ["provider"],
    registry=registry,
)
EMBED_CACHE_HIT = Counter(
    "somabrain_embed_cache_hit_total",
    "Embedding cache hits",
    ["provider"],
    registry=registry,
)

# Index/Compression configuration usage
INDEX_PROFILE_USE = Counter(
    "somabrain_index_profile_use_total",
    "Index/compression profile observed on startup",
    [
        "profile",
        "pq_m",
        "pq_bits",
        "opq",
        "anisotropic",
        "imi_cells",
        "hnsw_M",
        "hnsw_efs",
    ],
    registry=registry,
)

# Graph/link maintenance
LINK_DECAY_PRUNED = Counter(
    "somabrain_link_decay_pruned_total",
    "Count of graph links pruned by decay threshold",
    registry=registry,
)

# Audit pipeline metrics
AUDIT_KAFKA_PUBLISH = Counter(
    "somabrain_audit_kafka_publish_total",
    "Audit events successfully published to Kafka (best-effort)",
    registry=registry,
)

__all__ = [
    "EMBED_LAT",
    "EMBED_CACHE_HIT",
    "INDEX_PROFILE_USE",
    "LINK_DECAY_PRUNED",
    "AUDIT_KAFKA_PUBLISH",
]
