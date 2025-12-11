"""Novelty, SDR, and Recall Stage Metrics for SomaBrain.

This module provides metrics for novelty/error distributions,
SDR prefiltering, and recall stage latencies.

Metrics:
- NOVELTY_RAW: Histogram for raw novelty distribution
- ERROR_RAW: Histogram for raw prediction error distribution
- NOVELTY_NORM: Histogram for normalized novelty (z-score)
- ERROR_NORM: Histogram for normalized prediction error (z-score)
- SDR_PREFILTER_LAT: Histogram for SDR prefilter latency
- SDR_CANDIDATES: Counter for SDR candidate coords selected
- RECALL_WM_LAT: Histogram for recall WM stage latency
- RECALL_LTM_LAT: Histogram for recall LTM stage latency
- RECALL_CACHE_HIT: Counter for recall cache hits
- RECALL_CACHE_MISS: Counter for recall cache misses
"""

from __future__ import annotations

from somabrain.metrics.core import Counter, Histogram, registry

# Novelty/Error distributions
NOVELTY_RAW = Histogram(
    "somabrain_novelty_raw",
    "Novelty raw distribution",
    buckets=[i / 20.0 for i in range(0, 21)],
    labelnames=["cohort"],
    registry=registry,
)
ERROR_RAW = Histogram(
    "somabrain_error_raw",
    "Prediction error raw distribution",
    buckets=[i / 20.0 for i in range(0, 21)],
    labelnames=["cohort"],
    registry=registry,
)
NOVELTY_NORM = Histogram(
    "somabrain_novelty_norm",
    "Novelty normalized (z-score) distribution",
    buckets=[-5 + i * 0.5 for i in range(0, 21)],
    labelnames=["cohort"],
    registry=registry,
)
ERROR_NORM = Histogram(
    "somabrain_error_norm",
    "Prediction error normalized (z-score) distribution",
    buckets=[-5 + i * 0.5 for i in range(0, 21)],
    labelnames=["cohort"],
    registry=registry,
)

# SDR metrics
SDR_PREFILTER_LAT = Histogram(
    "somabrain_sdr_prefilter_latency_seconds",
    "SDR prefilter latency",
    ["cohort"],
    registry=registry,
)
SDR_CANDIDATES = Counter(
    "somabrain_sdr_candidates_total",
    "SDR candidate coords selected",
    ["cohort"],
    registry=registry,
)

# Recall stage latencies (A/B cohort)
RECALL_WM_LAT = Histogram(
    "somabrain_recall_wm_latency_seconds",
    "Recall WM stage latency",
    ["cohort"],
    registry=registry,
)
RECALL_LTM_LAT = Histogram(
    "somabrain_recall_ltm_latency_seconds",
    "Recall LTM stage latency",
    ["cohort"],
    registry=registry,
)
RECALL_CACHE_HIT = Counter(
    "somabrain_recall_cache_hit_total",
    "Recall cache hits",
    ["cohort"],
    registry=registry,
)
RECALL_CACHE_MISS = Counter(
    "somabrain_recall_cache_miss_total",
    "Recall cache misses",
    ["cohort"],
    registry=registry,
)

__all__ = [
    "NOVELTY_RAW",
    "ERROR_RAW",
    "NOVELTY_NORM",
    "ERROR_NORM",
    "SDR_PREFILTER_LAT",
    "SDR_CANDIDATES",
    "RECALL_WM_LAT",
    "RECALL_LTM_LAT",
    "RECALL_CACHE_HIT",
    "RECALL_CACHE_MISS",
]
