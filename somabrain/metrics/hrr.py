"""HRR (Holographic Reduced Representation) and Unbind Metrics for SomaBrain.

This module provides metrics for HRR cleanup operations, context saturation,
reranking, and unbinding path observability.

Metrics:
- HRR_CLEANUP_USED: Times HRR cleanup was applied
- HRR_CLEANUP_SCORE: HRR cleanup top-1 cosine score
- HRR_CLEANUP_CALLS: Count of HRR cleanup invocations
- HRR_ANCHOR_SIZE: Number of HRR anchors observed per tenant
- HRR_CONTEXT_SAT: HRR context saturation (anchors/max_anchors)
- HRR_RERANK_APPLIED: Times HRR-first re-ranking was applied
- HRR_RERANK_LTM_APPLIED: Times HRR-first LTM re-ranking was applied
- HRR_RERANK_WM_SKIPPED: Times HRR WM rerank was skipped
- UNBIND_PATH: Unbind path selection counts
- UNBIND_WIENER_FLOOR: Wiener/MAP floor value used in denominator
- UNBIND_K_EST: Estimated number of superposed items (k_est)
- UNBIND_SPECTRAL_BINS_CLAMPED: Spectral bins clamped to avoid division by near-zero
- UNBIND_EPS_USED: Effective epsilon used in spectral denominator
- RECONSTRUCTION_COSINE: Cosine similarity between original and reconstructed vector
"""

from __future__ import annotations

from somabrain.metrics.core import registry, Counter, Gauge, Histogram

# ---------------------------------------------------------------------------
# HRR Cleanup Metrics
# ---------------------------------------------------------------------------

HRR_CLEANUP_USED = Counter(
    "somabrain_hrr_cleanup_used_total",
    "Times HRR cleanup was applied",
    registry=registry,
)

HRR_CLEANUP_SCORE = Histogram(
    "somabrain_hrr_cleanup_score",
    "HRR cleanup top-1 cosine score",
    buckets=[i / 20.0 for i in range(0, 21)],
    registry=registry,
)

HRR_CLEANUP_CALLS = Counter(
    "somabrain_hrr_cleanup_calls_total",
    "Count of HRR cleanup invocations",
    registry=registry,
)

HRR_ANCHOR_SIZE = Histogram(
    "somabrain_hrr_anchor_size",
    "Number of HRR anchors observed per tenant",
    buckets=[1, 10, 100, 1_000, 10_000],
    registry=registry,
)

HRR_CONTEXT_SAT = Histogram(
    "somabrain_hrr_context_saturation",
    "HRR context saturation (anchors/max_anchors)",
    buckets=[i / 20.0 for i in range(0, 21)],
    registry=registry,
)

# ---------------------------------------------------------------------------
# HRR Reranking Metrics
# ---------------------------------------------------------------------------

HRR_RERANK_APPLIED = Counter(
    "somabrain_hrr_rerank_applied_total",
    "Times HRR-first re-ranking was applied",
    registry=registry,
)

HRR_RERANK_LTM_APPLIED = Counter(
    "somabrain_hrr_rerank_ltm_applied_total",
    "Times HRR-first LTM re-ranking was applied",
    registry=registry,
)

HRR_RERANK_WM_SKIPPED = Counter(
    "somabrain_hrr_rerank_wm_skipped_total",
    "Times HRR WM rerank was skipped due to large margin",
    registry=registry,
)

# ---------------------------------------------------------------------------
# Unbinding Path and Parameters
# ---------------------------------------------------------------------------

UNBIND_PATH = Counter(
    "somabrain_unbind_path_total",
    "Unbind path selection counts",
    ["path"],
    registry=registry,
)

UNBIND_WIENER_FLOOR = Gauge(
    "somabrain_unbind_wiener_floor",
    "Wiener/MAP floor value used in denominator",
    registry=registry,
)

UNBIND_K_EST = Gauge(
    "somabrain_unbind_k_est",
    "Estimated number of superposed items (k_est)",
    registry=registry,
)

# ---------------------------------------------------------------------------
# Additional Unbind Observability
# ---------------------------------------------------------------------------

UNBIND_SPECTRAL_BINS_CLAMPED = Counter(
    "somabrain_spectral_bins_clamped_total",
    "Number of spectral bins clamped/nudged to avoid division by near-zero",
    registry=registry,
)

UNBIND_EPS_USED = Gauge(
    "somabrain_unbind_eps_used",
    "Effective epsilon (power units) used in spectral denominator",
    registry=registry,
)

RECONSTRUCTION_COSINE = Histogram(
    "somabrain_reconstruction_cosine",
    "Cosine similarity between original and reconstructed vector after unbind",
    registry=registry,
)

__all__ = [
    # HRR Cleanup
    "HRR_CLEANUP_USED",
    "HRR_CLEANUP_SCORE",
    "HRR_CLEANUP_CALLS",
    "HRR_ANCHOR_SIZE",
    "HRR_CONTEXT_SAT",
    # HRR Reranking
    "HRR_RERANK_APPLIED",
    "HRR_RERANK_LTM_APPLIED",
    "HRR_RERANK_WM_SKIPPED",
    # Unbind
    "UNBIND_PATH",
    "UNBIND_WIENER_FLOOR",
    "UNBIND_K_EST",
    "UNBIND_SPECTRAL_BINS_CLAMPED",
    "UNBIND_EPS_USED",
    "RECONSTRUCTION_COSINE",
]
