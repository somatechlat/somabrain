"""Recall Quality and Capacity Metrics for SomaBrain.

This module provides metrics for recall quality assessment,
rate limiting, and quota management.

Metrics:
- RECALL_MARGIN_TOP12: Histogram for margin between top1 and top2 scores
- RECALL_SIM_TOP1: Histogram for top-1 recall similarity
- RECALL_SIM_TOPK_MEAN: Histogram for mean top-k similarity
- RERANK_CONTRIB: Histogram for re-ranking contribution
- DIVERSITY_PAIRWISE_MEAN: Histogram for pairwise diversity
- STORAGE_REDUCTION_RATIO: Gauge for storage efficiency
- RATE_LIMITED_TOTAL: Counter for rate-limited requests
- QUOTA_DENIED_TOTAL: Counter for quota-denied requests
- QUOTA_RESETS: Counter for quota reset operations
- QUOTA_ADJUSTMENTS: Counter for quota adjustments
"""

from __future__ import annotations

from somabrain.metrics.core import Counter, Gauge, Histogram, registry

# Decision attribution / recall quality
RECALL_MARGIN_TOP12 = Histogram(
    "somabrain_recall_margin_top1_top2",
    "Margin between top1 and top2 recall scores",
    registry=registry,
)
RECALL_SIM_TOP1 = Histogram(
    "somabrain_recall_sim_top1",
    "Top-1 recall score/similarity",
    registry=registry,
)
RECALL_SIM_TOPK_MEAN = Histogram(
    "somabrain_recall_sim_topk_mean",
    "Mean similarity of returned WM top-k",
    registry=registry,
)
RERANK_CONTRIB = Histogram(
    "somabrain_rerank_contrib",
    "Approx. contribution of re-ranking to final score",
    registry=registry,
)
DIVERSITY_PAIRWISE_MEAN = Histogram(
    "somabrain_diversity_pairwise_mean",
    "Mean pairwise cosine distance among returned set",
    registry=registry,
)

# Storage efficiency
STORAGE_REDUCTION_RATIO = Gauge(
    "somabrain_storage_reduction_ratio",
    "Observed storage reduction ratio (post/pre). Higher is better.",
    registry=registry,
)

# Capacity / backpressure
RATE_LIMITED_TOTAL = Counter(
    "somabrain_rate_limited_total",
    "Requests rejected by rate limiting",
    ["path"],
    registry=registry,
)
QUOTA_DENIED_TOTAL = Counter(
    "somabrain_quota_denied_total",
    "Write requests rejected by quota",
    ["reason"],
    registry=registry,
)
QUOTA_RESETS = Counter(
    "somabrain_quota_resets_total",
    "Admin quota reset operations",
    ["tenant_id"],
    registry=registry,
)
QUOTA_ADJUSTMENTS = Counter(
    "somabrain_quota_adjustments_total",
    "Admin quota adjustment operations",
    ["tenant_id"],
    registry=registry,
)

# Retrieval fusion metrics
RETRIEVAL_FUSION_APPLIED = Counter(
    "somabrain_retrieval_fusion_applied_total",
    "Times rank fusion was applied",
    ["method"],
    registry=registry,
)
RETRIEVAL_FUSION_SOURCES = Histogram(
    "somabrain_retrieval_fusion_sources",
    "Number of retriever sources fused",
    buckets=[1, 2, 3, 4, 5, 6],
    registry=registry,
)

__all__ = [
    "RECALL_MARGIN_TOP12",
    "RECALL_SIM_TOP1",
    "RECALL_SIM_TOPK_MEAN",
    "RERANK_CONTRIB",
    "DIVERSITY_PAIRWISE_MEAN",
    "STORAGE_REDUCTION_RATIO",
    "RATE_LIMITED_TOTAL",
    "QUOTA_DENIED_TOTAL",
    "QUOTA_RESETS",
    "QUOTA_ADJUSTMENTS",
    "RETRIEVAL_FUSION_APPLIED",
    "RETRIEVAL_FUSION_SOURCES",
]