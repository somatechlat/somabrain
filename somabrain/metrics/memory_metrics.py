"""Memory System Metrics for SomaBrain.

This module contains all metrics related to memory operations:
- Working Memory (WM) metrics
- Long-Term Memory (LTM) metrics
- Recall and retrieval metrics
- ANN (Approximate Nearest Neighbor) metrics
- Memory HTTP client metrics
- Governance metrics (items, eta, sparsity, margin)

Helper functions for recording memory-related metrics are also provided.
"""

from __future__ import annotations

from somabrain.metrics.core import (
    Counter,
    Gauge,
    Histogram,
    get_counter,
    get_gauge,
    get_histogram,
    registry,
)


# ---------------------------------------------------------------------------
# Working Memory Metrics
# ---------------------------------------------------------------------------

WM_HITS = Counter(
    "somabrain_wm_hits_total",
    "WM recall hits",
    registry=registry,
)

WM_MISSES = Counter(
    "somabrain_wm_misses_total",
    "WM recall misses",
    registry=registry,
)

WM_ADMIT = Counter(
    "somabrain_wm_admit_total",
    "Working Memory admissions",
    ["source"],
    registry=registry,
)

WM_UTILIZATION = Gauge(
    "somabrain_wm_utilization",
    "Working Memory utilization (items/capacity)",
    registry=registry,
)

WM_EVICTIONS = Counter(
    "somabrain_wm_evictions_total",
    "Working Memory evictions (best-effort)",
    registry=registry,
)


# ---------------------------------------------------------------------------
# Recall and Retrieval Metrics
# ---------------------------------------------------------------------------

RECALL_REQUESTS = get_counter(
    "somabrain_recall_requests_total",
    "Number of /recall requests",
    labelnames=["namespace"],
)

RECALL_LATENCY = get_histogram(
    "somabrain_recall_latency_seconds",
    "End-to-end recall latency",
    ["namespace"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0),
)

RETRIEVAL_REQUESTS = get_counter(
    "somabrain_retrieval_requests",
    "Retrieval requests",
    labelnames=["namespace", "retrievers"],
)

RETRIEVAL_LATENCY = get_histogram(
    "somabrain_retrieval_latency_seconds",
    "Retrieval pipeline latency",
)

RETRIEVAL_CANDIDATES = get_histogram(
    "somabrain_retrieval_candidates_total",
    "Retrieval candidate count after dedupe/rerank",
    buckets=[1, 3, 5, 10, 20, 50],
)

RETRIEVAL_PERSIST = get_counter(
    "somabrain_retrieval_persist_total",
    "Retrieval session persistence outcomes",
    labelnames=["status"],
)

RETRIEVAL_EMPTY = get_counter(
    "somabrain_retrieval_empty_total",
    "Retrieval requests returning zero candidates",
    labelnames=["namespace", "retrievers"],
)

RETRIEVER_HITS = get_counter(
    "somabrain_retriever_hits_total",
    "Per-retriever non-empty candidate lists",
    labelnames=["namespace", "retriever"],
)

RETRIEVER_LATENCY = get_histogram(
    "somabrain_retriever_latency_seconds",
    "Latency of individual retriever adapters",
    labelnames=["namespace", "retriever"],
    buckets=(0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.25, 0.5, 1.0),
)

# Fusion metrics
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

# Phase 0 — A/B + stage metrics
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


# ---------------------------------------------------------------------------
# ANN (Approximate Nearest Neighbor) Metrics
# ---------------------------------------------------------------------------

ANN_LATENCY = get_histogram(
    "somabrain_ann_latency_seconds",
    "ANN lookup latency",
    ["namespace"],
    buckets=(0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.25, 0.5),
)

ANN_REBUILD_TOTAL = get_counter(
    "somabrain_ann_rebuild_total",
    "Number of ANN rebuild operations",
    ["tenant", "namespace", "backend"],
)

ANN_REBUILD_SECONDS = get_histogram(
    "somabrain_ann_rebuild_seconds",
    "Duration of ANN rebuild operations",
    ["tenant", "namespace"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0),
)


# ---------------------------------------------------------------------------
# LTM Store Metrics
# ---------------------------------------------------------------------------

LTM_STORE_LAT = Histogram(
    "somabrain_ltm_store_latency_seconds",
    "Latency of LTM store operations",
    registry=registry,
)


# ---------------------------------------------------------------------------
# Memory HTTP Client Metrics
# ---------------------------------------------------------------------------

MEMORY_HTTP_REQUESTS = Counter(
    "somabrain_memory_http_requests_total",
    "Count of HTTP operations issued to the external memory service.",
    ["operation", "tenant", "status"],
    registry=registry,
)

MEMORY_HTTP_LATENCY = Histogram(
    "somabrain_memory_http_latency_seconds",
    "Latency distribution for memory HTTP operations.",
    ["operation", "tenant"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=registry,
)

# HTTP failures - import from metrics_original to avoid duplicate registration
# This metric uses the global REGISTRY, not our custom registry
from somabrain.metrics.core import REGISTRY

try:
    from prometheus_client import Counter as _PromCounter

    if "memory_http_failures_total" in REGISTRY._names_to_collectors:
        HTTP_FAILURES = REGISTRY._names_to_collectors["memory_http_failures_total"]
    else:
        HTTP_FAILURES = _PromCounter(
            "memory_http_failures_total",
            "Total number of failed HTTP calls to the external memory service",
            registry=REGISTRY,
        )
except Exception:
    # Fallback: create a no-op metric when Prometheus registry has conflicts.
    # Type ignore: None is intentional fallback; callers must check before use.
    HTTP_FAILURES = None  # type: ignore[assignment]

CIRCUIT_BREAKER_STATE = Gauge(
    "somabrain_memory_circuit_breaker_state",
    "The state of the memory service circuit breaker (1=open, 0=closed).",
    registry=registry,
)

MEMORY_OUTBOX_SYNC_TOTAL = Counter(
    "somabrain_memory_outbox_sync_total",
    "Total number of memory sync operations from the outbox (legacy gauge removed).",
    ["status"],
    registry=registry,
)


# ---------------------------------------------------------------------------
# Governance Metrics
# ---------------------------------------------------------------------------

MEMORY_ITEMS = get_gauge(
    "somabrain_memory_items",
    "Active items tracked per tenant/namespace",
    ["tenant", "namespace"],
)

ETA_GAUGE = get_gauge(
    "somabrain_eta",
    "Effective learning rate per tenant/namespace",
    ["tenant", "namespace"],
)

SPARSITY_GAUGE = get_gauge(
    "somabrain_sparsity",
    "Configured sparsity per tenant/namespace",
    ["tenant", "namespace"],
)

MARGIN_MEAN = get_gauge(
    "somabrain_cosine_margin_mean",
    "Rolling cosine margin per tenant/namespace",
    ["tenant", "namespace"],
)

CONFIG_VERSION = get_gauge(
    "somabrain_config_version",
    "Latest applied configuration version",
    ["tenant", "namespace"],
)

CONTROLLER_CHANGES = get_counter(
    "somabrain_controller_changes_total",
    "Supervisor parameter adjustments",
    ["parameter"],
)

# Storage efficiency
STORAGE_REDUCTION_RATIO = Gauge(
    "somabrain_storage_reduction_ratio",
    "Observed storage reduction ratio (post/pre). Higher is better if defined as retained fraction.",
    registry=registry,
)

# Graph/link maintenance
LINK_DECAY_PRUNED = Counter(
    "somabrain_link_decay_pruned_total",
    "Count of graph links pruned by decay threshold",
    registry=registry,
)


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def record_memory_snapshot(
    tenant: str,
    namespace: str,
    *,
    items: float | int | None = None,
    eta: float | None = None,
    sparsity: float | None = None,
    margin: float | None = None,
    config_version: float | int | None = None,
) -> None:
    """Update governance metrics for a tenant/namespace pair."""
    t = str(tenant or "").strip() or "unknown"
    ns = str(namespace or "").strip() or "default"

    try:
        if items is not None:
            MEMORY_ITEMS.labels(tenant=t, namespace=ns).set(float(items))
        if eta is not None:
            ETA_GAUGE.labels(tenant=t, namespace=ns).set(float(eta))
        if sparsity is not None:
            SPARSITY_GAUGE.labels(tenant=t, namespace=ns).set(float(sparsity))
        if margin is not None:
            MARGIN_MEAN.labels(tenant=t, namespace=ns).set(float(margin))
        if config_version is not None:
            CONFIG_VERSION.labels(tenant=t, namespace=ns).set(float(config_version))
    except Exception:
        pass


def observe_recall_latency(namespace: str, latency_seconds: float) -> None:
    """Record recall latency histogram sample for a namespace."""
    ns = str(namespace or "").strip() or "default"
    try:
        RECALL_LATENCY.labels(namespace=ns).observe(float(max(0.0, latency_seconds)))
    except Exception:
        pass


def observe_ann_latency(namespace: str, latency_seconds: float) -> None:
    """Record ANN lookup latency for a namespace."""
    ns = str(namespace or "").strip() or "default"
    try:
        ANN_LATENCY.labels(namespace=ns).observe(float(max(0.0, latency_seconds)))
    except Exception:
        pass


def mark_controller_change(parameter: str) -> None:
    """Increment supervisor change counter for a configuration parameter."""
    name = str(parameter or "unknown").strip() or "unknown"
    try:
        CONTROLLER_CHANGES.labels(parameter=name).inc()
    except Exception:
        pass


__all__ = [
    # WM metrics
    "WM_HITS",
    "WM_MISSES",
    "WM_ADMIT",
    "WM_UTILIZATION",
    "WM_EVICTIONS",
    # Recall/retrieval
    "RECALL_REQUESTS",
    "RECALL_LATENCY",
    "RETRIEVAL_REQUESTS",
    "RETRIEVAL_LATENCY",
    "RETRIEVAL_CANDIDATES",
    "RETRIEVAL_PERSIST",
    "RETRIEVAL_EMPTY",
    "RETRIEVER_HITS",
    "RETRIEVER_LATENCY",
    "RETRIEVAL_FUSION_APPLIED",
    "RETRIEVAL_FUSION_SOURCES",
    "RECALL_MARGIN_TOP12",
    "RECALL_SIM_TOP1",
    "RECALL_SIM_TOPK_MEAN",
    "RERANK_CONTRIB",
    "DIVERSITY_PAIRWISE_MEAN",
    "RECALL_WM_LAT",
    "RECALL_LTM_LAT",
    "RECALL_CACHE_HIT",
    "RECALL_CACHE_MISS",
    # ANN
    "ANN_LATENCY",
    "ANN_REBUILD_TOTAL",
    "ANN_REBUILD_SECONDS",
    # LTM
    "LTM_STORE_LAT",
    # HTTP client
    "MEMORY_HTTP_REQUESTS",
    "MEMORY_HTTP_LATENCY",
    "HTTP_FAILURES",
    "CIRCUIT_BREAKER_STATE",
    "MEMORY_OUTBOX_SYNC_TOTAL",
    # Governance
    "MEMORY_ITEMS",
    "ETA_GAUGE",
    "SPARSITY_GAUGE",
    "MARGIN_MEAN",
    "CONFIG_VERSION",
    "CONTROLLER_CHANGES",
    "STORAGE_REDUCTION_RATIO",
    "LINK_DECAY_PRUNED",
    # Helper functions
    "record_memory_snapshot",
    "observe_recall_latency",
    "observe_ann_latency",
    "mark_controller_change",
]
