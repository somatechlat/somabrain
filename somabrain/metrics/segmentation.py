"""Segmentation and Fusion Metrics for SomaBrain.

This module provides metrics for HMM segmentation boundaries
and fusion weight normalization.

Metrics:
- SEGMENTATION_BOUNDARIES_PER_HOUR: Gauge for boundaries per hour
- SEGMENTATION_DUPLICATE_RATIO: Gauge for duplicate boundary ratio
- SEGMENTATION_HMM_STATE_VOLATILE: Gauge for HMM volatile state probability
- SEGMENTATION_MAX_DWELL_EXCEEDED: Counter for max dwell threshold breaches
- FUSION_WEIGHT_NORM_ERROR: Gauge for fusion weight normalization error
- FUSION_ALPHA_ADAPTIVE: Gauge for adaptive alpha parameter
- FUSION_SOFTMAX_WEIGHT: Gauge for final softmax weights
"""

from __future__ import annotations

from somabrain.metrics.core import Counter, Gauge, registry

# Segmentation HMM Metrics
SEGMENTATION_BOUNDARIES_PER_HOUR = Gauge(
    "somabrain_segmentation_boundaries_per_hour",
    "Segmentation boundaries emitted per hour by tenant:domain",
    labelnames=["tenant", "domain"],
    registry=registry,
)
SEGMENTATION_DUPLICATE_RATIO = Gauge(
    "somabrain_segmentation_duplicate_ratio",
    "Ratio of duplicate boundaries to total boundaries by tenant:domain",
    labelnames=["tenant", "domain"],
    registry=registry,
)
SEGMENTATION_HMM_STATE_VOLATILE = Gauge(
    "somabrain_segmentation_hmm_state_volatile",
    "Current HMM state probability for VOLATILE (1=fully volatile, 0=fully stable)",
    labelnames=["tenant", "domain"],
    registry=registry,
)
SEGMENTATION_MAX_DWELL_EXCEEDED = Counter(
    "somabrain_segmentation_max_dwell_exceeded_total",
    "Count of boundaries forced by max dwell threshold",
    labelnames=["tenant", "domain"],
    registry=registry,
)

# Fusion Normalization Metrics
FUSION_WEIGHT_NORM_ERROR = Gauge(
    "somabrain_fusion_weight_norm_error",
    "Normalized error per domain for fusion weighting",
    labelnames=["tenant", "domain"],
    registry=registry,
)
FUSION_ALPHA_ADAPTIVE = Gauge(
    "somabrain_fusion_alpha_adaptive",
    "Current adaptive alpha parameter for fusion normalization",
    labelnames=["tenant"],
    registry=registry,
)
FUSION_SOFTMAX_WEIGHT = Gauge(
    "somabrain_fusion_softmax_weight",
    "Final softmax weight assigned to each domain",
    labelnames=["tenant", "domain"],
    registry=registry,
)

__all__ = [
    "SEGMENTATION_BOUNDARIES_PER_HOUR",
    "SEGMENTATION_DUPLICATE_RATIO",
    "SEGMENTATION_HMM_STATE_VOLATILE",
    "SEGMENTATION_MAX_DWELL_EXCEEDED",
    "FUSION_WEIGHT_NORM_ERROR",
    "FUSION_ALPHA_ADAPTIVE",
    "FUSION_SOFTMAX_WEIGHT",
]
