"""
Metrics Module for SomaBrain.

This module provides comprehensive metrics collection and monitoring for the SomaBrain system
using Prometheus client library. It includes HTTP request metrics, cognitive performance metrics,
and system health monitoring with automatic FastAPI integration.

Key Features:
- Prometheus-compatible metrics collection
- HTTP request latency and count tracking
- Cognitive metrics (salience, novelty, prediction error)
- Memory system performance monitoring
- Embedding and indexing metrics
- Consolidation and sleep cycle tracking
- Automatic middleware integration for request timing

Metrics Categories:
- HTTP Metrics: Request counts, latency, status codes
- Working Memory: Hit/miss rates, latency
- Salience: Score distributions, threshold tracking
- HRR System: Cleanup usage, anchor saturation, reranking
- Prediction: Latency by provider, fallback counts
- Consolidation: Run counts, replay strength, REM synthesis
- Supervisor: Free energy, neuromodulator modulation
- Executive Controller: Conflict detection, bandit rewards
- Microcircuits: Vote entropy, column admissions
- Embeddings: Latency by provider, cache hits
- Journal: Append/replay/skip counts, rotations

Functions:
    metrics_endpoint: FastAPI endpoint for exposing Prometheus metrics.
    timing_middleware: FastAPI middleware for automatic request timing.
"""

from __future__ import annotations

import time
import os
from threading import Lock
from typing import Any, Awaitable, Callable, Iterable
import builtins as _builtins

try:
    from prometheus_client import (
        CONTENT_TYPE_LATEST,
        REGISTRY,
        CollectorRegistry,
        Counter as _PromCounter,
        Gauge as _PromGauge,
        Histogram as _PromHistogram,
        Summary as _PromSummary,
        generate_latest,
    )
except Exception:  # pragma: no cover
    # Enforce "no fake fallbacks" by default. Allow a noop shim only in docs builds
    # or when explicitly permitted via SOMABRAIN_ALLOW_METRICS_NOOP=1.
    allow_noop = False
    try:
        allow_noop = bool(os.getenv("SPHINX_BUILD")) or (
            (os.getenv("SOMABRAIN_ALLOW_METRICS_NOOP", "").strip().lower())
            in ("1", "true", "yes", "on")
        )
    except Exception:
        allow_noop = False

    if not allow_noop:
        raise ImportError(
            "prometheus_client is required for somabrain.metrics; set SOMABRAIN_ALLOW_METRICS_NOOP=1 only for docs/tests if you must bypass"
        )

    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"

    class CollectorRegistry:  # minimal shim for docs/tests only
        def __init__(self):
            self._names_to_collectors = {}

    class _NoopMetric:
        def __init__(self, *args, **kwargs):
            pass

        def inc(self, *a, **k):
            pass

        def set(self, *a, **k):
            pass

        def labels(self, *a, **k):
            return self

        def observe(self, *a, **k):
            pass

    REGISTRY = CollectorRegistry()
    _PromCounter = _NoopMetric
    _PromGauge = _NoopMetric
    _PromHistogram = _NoopMetric

    def generate_latest(reg):
        return b""


# Aliases used later (avoid interleaved imports)

# Share a single registry across module reloads/process components.
try:
    _reg = getattr(_builtins, "_SOMABRAIN_METRICS_REGISTRY")
except Exception:
    _reg = None
if not _reg:
    _reg = CollectorRegistry()
    try:
        setattr(_builtins, "_SOMABRAIN_METRICS_REGISTRY", _reg)
    except Exception:
        pass
registry = _reg


def _get_existing(name: str):
    # Prefer the app registry mapping if present; fall back to global REGISTRY
    try:
        return registry._names_to_collectors.get(name)
    except Exception:
        try:
            return REGISTRY._names_to_collectors.get(name)
        except Exception:
            return None


def _counter(name: str, documentation: str, *args, **kwargs):
    existing = _get_existing(name)
    if existing is not None:
        return existing

    if "registry" not in kwargs:
        kwargs["registry"] = registry
    return _PromCounter(name, documentation, *args, **kwargs)


def _gauge(name: str, documentation: str, *args, **kwargs):
    existing = _get_existing(name)
    if existing is not None:
        return existing

    if "registry" not in kwargs:
        kwargs["registry"] = registry
    return _PromGauge(name, documentation, *args, **kwargs)


def _histogram(name: str, documentation: str, *args, **kwargs):
    existing = _get_existing(name)
    if existing is not None:
        return existing

    if "registry" not in kwargs:
        kwargs["registry"] = registry
    return _PromHistogram(name, documentation, *args, **kwargs)


def _summary(name: str, documentation: str, *args, **kwargs):
    existing = _get_existing(name)
    if existing is not None:
        return existing
    if "registry" not in kwargs:
        kwargs["registry"] = registry
    return _PromSummary(name, documentation, *args, **kwargs)


def get_counter(name: str, documentation: str, labelnames: list | None = None):
    """Get or create a Counter in the central registry.

    Returns an existing collector if already registered, otherwise creates and
    registers a new Counter attached to the central `registry`.
    """
    existing = _get_existing(name)
    if existing is not None:
        return existing

    if labelnames:
        return _counter(name, documentation, labelnames, registry=registry)
    return _counter(name, documentation, registry=registry)


def get_gauge(name: str, documentation: str, labelnames: list | None = None):
    existing = _get_existing(name)
    if existing is not None:
        return existing

    if labelnames:
        return _gauge(name, documentation, labelnames, registry=registry)
    return _gauge(name, documentation, registry=registry)


def get_histogram(
    name: str, documentation: str, labelnames: list | None = None, **kwargs
):
    existing = _get_existing(name)
    if existing is not None:
        return existing

    if labelnames:
        return _histogram(name, documentation, labelnames, registry=registry, **kwargs)
    return _histogram(name, documentation, registry=registry, **kwargs)


_external_metrics_lock = Lock()
_external_metrics_scraped: dict[str, float] = {}
_DEFAULT_EXTERNAL_METRICS = ("kafka", "postgres", "opa")


# Rebind public constructors to safe wrappers for in-module usage.
Counter = _counter
Gauge = _gauge
Histogram = _histogram
Summary = _summary

# Aliases used later (avoid interleaved imports)
_Hist = Histogram
_PC = Counter
_PHist = Histogram
_PCounter = Counter


HTTP_COUNT = Counter(
    "somabrain_http_requests_total",
    "HTTP requests",
    ["method", "path", "status"],
    registry=registry,
)
HTTP_LATENCY = Histogram(
    "somabrain_http_latency_seconds",
    "HTTP request latency",
    ["method", "path"],
    registry=registry,
)
# OPA enforcement metrics – count allow and deny decisions
OPA_ALLOW_TOTAL = get_counter(
    "somabrain_opa_allow_total",
    "Number of requests allowed by OPA",
)
OPA_DENY_TOTAL = get_counter(
    "somabrain_opa_deny_total",
    "Number of requests denied by OPA",
)
# Reward Gate metrics – count allow and deny decisions
REWARD_ALLOW_TOTAL = get_counter(
    "somabrain_reward_allow_total",
    "Number of requests allowed by Reward Gate",
)
REWARD_DENY_TOTAL = get_counter(
    "somabrain_reward_deny_total",
    "Number of requests denied by Reward Gate",
)
# Constitution metrics (baseline)
CONSTITUTION_VERIFIED = Gauge(
    "somabrain_constitution_verified",
    "Constitution verification status (1=verified, 0=unverified)",
    registry=registry,
)
CONSTITUTION_VERIFY_LATENCY = Histogram(
    "somabrain_constitution_verify_latency_seconds",
    "Time spent verifying constitution signatures on startup",
    registry=registry,
)
# Utility metrics (Phase A)
UTILITY_NEGATIVE = Counter(
    "somabrain_utility_negative_total",
    "Times utility guard rejected a request (U < 0)",
    registry=registry,
)
UTILITY_VALUE = Gauge(
    "somabrain_utility_value",
    "Last computed utility value (per process)",
    registry=registry,
)
WM_HITS = Counter("somabrain_wm_hits_total", "WM recall hits", registry=registry)
WM_MISSES = Counter("somabrain_wm_misses_total", "WM recall misses", registry=registry)
SALIENCE_STORE = Counter(
    "somabrain_store_events_total", "Stores gated by salience", registry=registry
)

SALIENCE_HIST = _Hist(
    "somabrain_salience_score",
    "Salience score distribution",
    buckets=[i / 20.0 for i in range(0, 21)],
    registry=registry,
)
FD_ENERGY_CAPTURE = Gauge(
    "somabrain_fd_energy_capture_ratio",
    "FD salience sketch energy capture ratio",
    registry=registry,
)
FD_RESIDUAL = _Hist(
    "somabrain_fd_residual_ratio",
    "Residual energy ratio per vector for FD salience",
    buckets=[i / 20.0 for i in range(0, 21)],
    registry=registry,
)
FD_TRACE_ERROR = Gauge(
    "somabrain_fd_trace_norm_error",
    "Trace normalization error for FD sketch",
    registry=registry,
)
FD_PSD_INVARIANT = Gauge(
    "somabrain_fd_psd_invariant",
    "PSD invariant flag for FD sketch (1=ok, 0=violation)",
    registry=registry,
)
SCORER_COMPONENT = _Hist(
    "somabrain_scorer_component",
    "Unified scorer component values",
    ["component"],
    buckets=[i / 10.0 for i in range(-10, 11)],
    registry=registry,
)
SCORER_FINAL = _Hist(
    "somabrain_scorer_final",
    "Unified scorer combined score",
    buckets=[i / 20.0 for i in range(0, 21)],
    registry=registry,
)
SCORER_WEIGHT_CLAMPED = Counter(
    "somabrain_scorer_weight_clamped_total",
    "Unified scorer weight clamp events",
    ["component", "bound"],
    registry=registry,
)

EXTERNAL_METRICS_SCRAPE_STATUS = get_gauge(
    "somabrain_external_metrics_scraped",
    "Flag indicating that an external exporter has been scraped at least once",
    ["source"],
)

# WM admissions and attention level
WM_ADMIT = Counter(
    "somabrain_wm_admit_total",
    "Working Memory admissions",
    ["source"],
    registry=registry,
)
ATTENTION_LEVEL = Gauge(
    "somabrain_attention_level",
    "Current attention level as tracked by thalamus (0..1)",
    registry=registry,
)

# HRR cleanup metrics
HRR_CLEANUP_USED = Counter(
    "somabrain_hrr_cleanup_used_total",
    "Times HRR cleanup was applied",
    registry=registry,
)
HRR_CLEANUP_SCORE = _Hist(
    "somabrain_hrr_cleanup_score",
    "HRR cleanup top-1 cosine score",
    buckets=[i / 20.0 for i in range(0, 21)],
    registry=registry,
)

HRR_CLEANUP_CALLS = _PC(
    "somabrain_hrr_cleanup_calls_total",
    "Count of HRR cleanup invocations",
    registry=registry,
)
HRR_ANCHOR_SIZE = _Hist(
    "somabrain_hrr_anchor_size",
    "Number of HRR anchors observed per tenant",
    buckets=[1, 10, 100, 1_000, 10_000],
    registry=registry,
)
HRR_CONTEXT_SAT = _Hist(
    "somabrain_hrr_context_saturation",
    "HRR context saturation (anchors/max_anchors)",
    buckets=[i / 20.0 for i in range(0, 21)],
    registry=registry,
)

# Governance metrics (Sprint E1)
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
RECALL_LATENCY = get_histogram(
    "somabrain_recall_latency_seconds",
    "End-to-end recall latency",
    ["namespace"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0),
)
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

# Phase 0 — A/B + stage metrics

RECALL_WM_LAT = _PHist(
    "somabrain_recall_wm_latency_seconds",
    "Recall WM stage latency",
    ["cohort"],
    registry=registry,
)
RECALL_LTM_LAT = _PHist(
    "somabrain_recall_ltm_latency_seconds",
    "Recall LTM stage latency",
    ["cohort"],
    registry=registry,
)

RECALL_CACHE_HIT = _PCounter(
    "somabrain_recall_cache_hit_total",
    "Recall cache hits",
    ["cohort"],
    registry=registry,
)
RECALL_CACHE_MISS = _PCounter(
    "somabrain_recall_cache_miss_total",
    "Recall cache misses",
    ["cohort"],
    registry=registry,
)
NOVELTY_RAW = _Hist(
    "somabrain_novelty_raw",
    "Novelty raw distribution",
    buckets=[i / 20.0 for i in range(0, 21)],
    labelnames=["cohort"],
    registry=registry,
)
ERROR_RAW = _Hist(
    "somabrain_error_raw",
    "Prediction error raw distribution",
    buckets=[i / 20.0 for i in range(0, 21)],
    labelnames=["cohort"],
    registry=registry,
)
NOVELTY_NORM = _Hist(
    "somabrain_novelty_norm",
    "Novelty normalized (z-score) distribution",
    buckets=[-5 + i * 0.5 for i in range(0, 21)],
    labelnames=["cohort"],
    registry=registry,
)
ERROR_NORM = _Hist(
    "somabrain_error_norm",
    "Prediction error normalized (z-score) distribution",
    buckets=[-5 + i * 0.5 for i in range(0, 21)],
    labelnames=["cohort"],
    registry=registry,
)
SDR_PREFILTER_LAT = _PHist(
    "somabrain_sdr_prefilter_latency_seconds",
    "SDR prefilter latency",
    ["cohort"],
    registry=registry,
)
SDR_CANDIDATES = _PCounter(
    "somabrain_sdr_candidates_total",
    "SDR candidate coords selected",
    ["cohort"],
    registry=registry,
)
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

# Unbinding path + parameters
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

# --- Retrieval metrics ---
RECALL_REQUESTS = get_counter(
    "somabrain_recall_requests_total",
    "Number of /memory/recall requests",
    labelnames=["namespace"],
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

# Per-retriever latency (adapter execution time)
RETRIEVER_LATENCY = get_histogram(
    "somabrain_retriever_latency_seconds",
    "Latency of individual retriever adapters",
    labelnames=["namespace", "retriever"],
    buckets=(0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.25, 0.5, 1.0),
)

# Fusion metrics (retrieval enhancements)
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

# Additional unbind observability
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

# Predictor metrics
PREDICTOR_LATENCY = Histogram(
    "somabrain_predictor_latency_seconds",
    "Predictor call latency",
    registry=registry,
)
PREDICTOR_LATENCY_BY = Histogram(
    "somabrain_predictor_latency_seconds_by",
    "Predictor call latency by provider",
    ["provider"],
    registry=registry,
)
PREDICTOR_FALLBACK = Counter(
    "somabrain_predictor_fallback_total",
    "Count of predictor timeouts/errors causing degrade",
    registry=registry,
)

# --- Planning KPIs ---
PLANNING_LATENCY = Histogram(
    "somabrain_planning_latency_seconds",
    "Planning generation latency seconds",
    ["backend"],
    buckets=(0.001, 0.005, 0.01, 0.02, 0.05, 0.075, 0.1, 0.2, 0.3, 0.5, 1.0),
    registry=registry,
)
PLANNING_LATENCY_P99 = Gauge(
    "somabrain_planning_latency_p99",
    "Approximate p99 planning latency seconds (rolling)",
    registry=registry,
)

_planning_samples: list[float] = []
_MAX_PLANNING_SAMPLES = 1000


def record_planning_latency(backend: str, latency_seconds: float) -> None:
    try:
        PLANNING_LATENCY.labels(backend=str(backend)).observe(float(latency_seconds))
        _planning_samples.append(float(latency_seconds))
        if len(_planning_samples) > _MAX_PLANNING_SAMPLES:
            del _planning_samples[: len(_planning_samples) - _MAX_PLANNING_SAMPLES]
        if _planning_samples:
            ordered = sorted(_planning_samples)
            idx = max(0, int(0.99 * (len(ordered) - 1)))
            PLANNING_LATENCY_P99.set(ordered[idx])
    except Exception:
        pass


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

# Storage efficiency KPI: ratio of post-compression bytes to pre-compression bytes
STORAGE_REDUCTION_RATIO = Gauge(
    "somabrain_storage_reduction_ratio",
    "Observed storage reduction ratio (post/pre). Higher is better if defined as retained fraction; dashboards invert to show savings.",
    registry=registry,
)

# Capacity / backpressure
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
LTM_STORE_LAT = Histogram(
    "somabrain_ltm_store_latency_seconds",
    "Latency of LTM store operations",
    registry=registry,
)
# Removed queued write semantics (fail-fast); metric deprecated.
# (Previously: somabrain_ltm_store_queued_total)

# Executive details
EXEC_K_SELECTED = Histogram(
    "somabrain_exec_k_selected",
    "Final top_k selected by executive/policy",
    registry=registry,
)

# Consolidation / Sleep metrics
CONSOLIDATION_RUNS = Counter(
    "somabrain_consolidation_runs_total",
    "Consolidation runs by phase",
    ["phase"],
    registry=registry,
)
REPLAY_STRENGTH = Histogram(
    "somabrain_consolidation_replay_strength",
    "Distribution of replay reinforcement weights",
    registry=registry,
)
REM_SYNTHESIZED = Counter(
    "somabrain_consolidation_rem_synthesized_total",
    "Count of REM synthesized semantic memories",
    registry=registry,
)

# Supervisor / Energy metrics
FREE_ENERGY = Histogram(
    "somabrain_free_energy",
    "Free-energy proxy values",
    registry=registry,
)
SUPERVISOR_MODULATION = Histogram(
    "somabrain_supervisor_modulation",
    "Magnitude of neuromodulator adjustments",
    registry=registry,
)

# Executive Controller metrics
EXEC_CONFLICT = Histogram(
    "somabrain_exec_conflict",
    "Executive conflict proxy (1-mean recall strength)",
    registry=registry,
)
EXEC_USE_GRAPH = Counter(
    "somabrain_exec_use_graph_total",
    "Times executive controller enabled graph augmentation",
    registry=registry,
)
EXEC_BANDIT_ARM = Counter(
    "somabrain_exec_bandit_arm_total",
    "Executive bandit arm selection counts",
    ["arm"],
    registry=registry,
)
EXEC_BANDIT_REWARD = Histogram(
    "somabrain_exec_bandit_reward",
    "Executive bandit observed rewards",
    registry=registry,
)

# Microcircuits
MICRO_VOTE_ENTROPY = Histogram(
    "somabrain_micro_vote_entropy",
    "Entropy of column vote distribution",
    registry=registry,
)
MICRO_COLUMN_ADMIT = Counter(
    "somabrain_micro_column_admit_total",
    "Admissions per microcircuit column",
    ["column"],
    registry=registry,
)
MICRO_COLUMN_BEST = Counter(
    "somabrain_micro_column_best_total",
    "Recall best-column selection counts",
    ["column"],
    registry=registry,
)

# Adaptive salience gauges
SALIENCE_THRESH_STORE = Gauge(
    "somabrain_salience_threshold_store",
    "Current store threshold",
    registry=registry,
)
SALIENCE_THRESH_ACT = Gauge(
    "somabrain_salience_threshold_act",
    "Current act threshold",
    registry=registry,
)
SALIENCE_STORE_RATE_OBS = Gauge(
    "somabrain_salience_store_rate_obs",
    "Observed EWMA store rate",
    registry=registry,
)
SALIENCE_ACT_RATE_OBS = Gauge(
    "somabrain_salience_act_rate_obs",
    "Observed EWMA act rate",
    registry=registry,
)

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

# Index/Compression configuration usage (ablation labels kept small & numeric)
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


# Audit pipeline metrics: Kafka publish path only (no local fallbacks)
AUDIT_KAFKA_PUBLISH = Counter(
    "somabrain_audit_kafka_publish_total",
    "Audit events successfully published to Kafka (best-effort)",
    registry=registry,
)

# New metrics for outbox and circuit breaker
# Ensure OUTBOX_PENDING gauge is only created once per process to avoid duplicate registration errors.
# The Prometheus client stores collectors in REGISTRY._names_to_collectors; we check for existing gauge.
if "memory_outbox_pending" in REGISTRY._names_to_collectors:
    OUTBOX_PENDING = REGISTRY._names_to_collectors["memory_outbox_pending"]
else:
    OUTBOX_PENDING = Gauge(
        "memory_outbox_pending",
        "Number of pending messages in the out‑box queue",
        registry=REGISTRY,
    )

# Ensure CIRCUIT_STATE gauge is only created once per process.
if "memory_circuit_state" in REGISTRY._names_to_collectors:
    CIRCUIT_STATE = REGISTRY._names_to_collectors["memory_circuit_state"]
else:
    CIRCUIT_STATE = Gauge(
        "memory_circuit_state",
        "Circuit breaker state for external memory service: 0=closed, 1=open",
        registry=REGISTRY,
    )
# Ensure HTTP_FAILURES counter is only created once per process.
if "memory_http_failures_total" in REGISTRY._names_to_collectors:
    HTTP_FAILURES = REGISTRY._names_to_collectors["memory_http_failures_total"]
else:
    HTTP_FAILURES = Counter(
        "memory_http_failures_total",
        "Total number of failed HTTP calls to the external memory service",
        registry=REGISTRY,
    )


# Neuromodulator value gauges (ensure single registration)
if "neuromod_dopamine" in REGISTRY._names_to_collectors:
    NEUROMOD_DOPAMINE = REGISTRY._names_to_collectors["neuromod_dopamine"]
else:
    NEUROMOD_DOPAMINE = Gauge(
        "neuromod_dopamine",
        "Current dopamine level",
        registry=REGISTRY,
    )
if "neuromod_serotonin" in REGISTRY._names_to_collectors:
    NEUROMOD_SEROTONIN = REGISTRY._names_to_collectors["neuromod_serotonin"]
else:
    NEUROMOD_SEROTONIN = Gauge(
        "neuromod_serotonin",
        "Current serotonin level",
        registry=REGISTRY,
    )
if "neuromod_noradrenaline" in REGISTRY._names_to_collectors:
    NEUROMOD_NORADRENALINE = REGISTRY._names_to_collectors["neuromod_noradrenaline"]
else:
    NEUROMOD_NORADRENALINE = Gauge(
        "neuromod_noradrenaline",
        "Current noradrenaline level",
        registry=REGISTRY,
    )
if "neuromod_acetylcholine" in REGISTRY._names_to_collectors:
    NEUROMOD_ACETYLCHOLINE = REGISTRY._names_to_collectors["neuromod_acetylcholine"]
else:
    NEUROMOD_ACETYLCHOLINE = Gauge(
        "neuromod_acetylcholine",
        "Current acetylcholine level",
        registry=REGISTRY,
    )
if "neuromod_updates_total" in REGISTRY._names_to_collectors:
    NEUROMOD_UPDATE_COUNT = REGISTRY._names_to_collectors["neuromod_updates_total"]
else:
    NEUROMOD_UPDATE_COUNT = Counter(
        "neuromod_updates_total",
        "Total number of neuromodulator updates",
        registry=REGISTRY,
    )

# ==============================
# Learning & Adaptation Metrics (Per-Tenant)
# ==============================

# Retrieval weights (per-tenant adaptation state)
LEARNING_RETRIEVAL_ALPHA = get_gauge(
    "somabrain_learning_retrieval_alpha",
    "Semantic weight in retrieval (α) per tenant",
    labelnames=["tenant_id"],
)
LEARNING_RETRIEVAL_BETA = get_gauge(
    "somabrain_learning_retrieval_beta",
    "Graph weight in retrieval (β) per tenant",
    labelnames=["tenant_id"],
)
LEARNING_RETRIEVAL_GAMMA = get_gauge(
    "somabrain_learning_retrieval_gamma",
    "Recent weight in retrieval (γ) per tenant",
    labelnames=["tenant_id"],
)
LEARNING_RETRIEVAL_TAU = get_gauge(
    "somabrain_learning_retrieval_tau",
    "Temperature for diversity (τ) per tenant",
    labelnames=["tenant_id"],
)

# Utility weights (per-tenant adaptation state)
LEARNING_UTILITY_LAMBDA = get_gauge(
    "somabrain_learning_utility_lambda",
    "Semantic utility weight (λ) per tenant",
    labelnames=["tenant_id"],
)
LEARNING_UTILITY_MU = get_gauge(
    "somabrain_learning_utility_mu",
    "Graph utility weight (μ) per tenant",
    labelnames=["tenant_id"],
)
LEARNING_UTILITY_NU = get_gauge(
    "somabrain_learning_utility_nu",
    "Recent utility weight (ν) per tenant",
    labelnames=["tenant_id"],
)
LEARNING_GAIN = get_gauge(
    "somabrain_learning_gain",
    "Configured adaptation gain per component",
    labelnames=["tenant_id", "component"],
)
LEARNING_BOUND = get_gauge(
    "somabrain_learning_bound",
    "Adaptation bounds per component and side",
    labelnames=["tenant_id", "component", "bound"],
)

# Feedback loop metrics
LEARNING_FEEDBACK_APPLIED = get_counter(
    "somabrain_learning_feedback_applied_total",
    "Total feedback applications (success) per tenant",
    labelnames=["tenant_id"],
)
LEARNING_FEEDBACK_REJECTED = get_counter(
    "somabrain_learning_feedback_rejected_total",
    "Feedback rejected due to outliers or bounds per tenant",
    labelnames=["tenant_id", "reason"],
)
LEARNING_FEEDBACK_LATENCY = get_histogram(
    "somabrain_learning_feedback_latency_seconds",
    "Latency of feedback application (end-to-end) per tenant",
    labelnames=["tenant_id"],
    buckets=[0.01, 0.05, 0.1, 0.2, 0.3, 0.5, 1.0, 2.0],
)

# Adaptation dynamics
LEARNING_EFFECTIVE_LR = get_gauge(
    "somabrain_learning_effective_lr",
    "Effective learning rate (lr_eff) per tenant",
    labelnames=["tenant_id"],
)
LEARNING_ROLLBACKS = get_counter(
    "somabrain_learning_rollbacks_total",
    "Number of weight rollbacks triggered per tenant",
    labelnames=["tenant_id"],
)

# Working memory growth
LEARNING_WM_LENGTH = get_gauge(
    "somabrain_learning_wm_length",
    "Working memory length per session/tenant",
    labelnames=["session_id", "tenant_id"],
)

# Autonomous experiments
LEARNING_EXPERIMENT_ACTIVE = get_gauge(
    "somabrain_learning_experiment_active",
    "Number of active A/B experiments",
    labelnames=["experiment_name"],
)
LEARNING_EXPERIMENT_PROMOTIONS = get_counter(
    "somabrain_learning_experiment_promotions_total",
    "Number of successful canary promotions",
    labelnames=["experiment_name"],
)


# ==============================
# Helper Functions for Learning Metrics
# ==============================


def update_learning_retrieval_weights(
    tenant_id: str, alpha: float, beta: float, gamma: float, tau: float
):
    """Update per-tenant retrieval weight metrics."""
    LEARNING_RETRIEVAL_ALPHA.labels(tenant_id=tenant_id).set(alpha)
    LEARNING_RETRIEVAL_BETA.labels(tenant_id=tenant_id).set(beta)
    LEARNING_RETRIEVAL_GAMMA.labels(tenant_id=tenant_id).set(gamma)
    LEARNING_RETRIEVAL_TAU.labels(tenant_id=tenant_id).set(tau)


def update_learning_utility_weights(
    tenant_id: str, lambda_: float, mu: float, nu: float
):
    """Update per-tenant utility weight metrics."""
    LEARNING_UTILITY_LAMBDA.labels(tenant_id=tenant_id).set(lambda_)
    LEARNING_UTILITY_MU.labels(tenant_id=tenant_id).set(mu)
    LEARNING_UTILITY_NU.labels(tenant_id=tenant_id).set(nu)


def update_learning_gains(tenant_id: str, **gains: float) -> None:
    """Record configured adaptation gains per component."""

    for component, value in gains.items():
        LEARNING_GAIN.labels(tenant_id=tenant_id, component=component).set(float(value))


def update_learning_bounds(tenant_id: str, **bounds: float) -> None:
    """Record adaptation bounds (min/max) for each component."""

    for key, value in bounds.items():
        if key.endswith("_min"):
            component = key[:-4]
            LEARNING_BOUND.labels(
                tenant_id=tenant_id, component=component, bound="min"
            ).set(float(value))
        elif key.endswith("_max"):
            component = key[:-4]
            LEARNING_BOUND.labels(
                tenant_id=tenant_id, component=component, bound="max"
            ).set(float(value))


def record_learning_feedback_applied(tenant_id: str):
    """Increment feedback applied counter for tenant."""
    LEARNING_FEEDBACK_APPLIED.labels(tenant_id=tenant_id).inc()


def record_learning_feedback_rejected(tenant_id: str, reason: str):
    """Increment feedback rejected counter for tenant."""
    LEARNING_FEEDBACK_REJECTED.labels(tenant_id=tenant_id, reason=reason).inc()


def record_learning_feedback_latency(tenant_id: str, latency_seconds: float):
    """Record feedback latency for tenant."""
    LEARNING_FEEDBACK_LATENCY.labels(tenant_id=tenant_id).observe(latency_seconds)


def update_learning_effective_lr(tenant_id: str, lr_eff: float):
    """Update effective learning rate metric for tenant."""
    LEARNING_EFFECTIVE_LR.labels(tenant_id=tenant_id).set(lr_eff)


# Phase‑1 adaptive knob metrics
tau_decay_events = get_counter(
    "somabrain_tau_decay_events_total",
    "Tau decay applications per tenant",
    labelnames=["tenant_id"],
)
tau_anneal_events = get_counter(
    "somabrain_tau_anneal_events_total",
    "Tau annealing applications per tenant (any schedule)",
    labelnames=["tenant_id"],
)
entropy_cap_events = get_counter(
    "somabrain_entropy_cap_events_total",
    "Entropy cap sharpen events per tenant",
    labelnames=["tenant_id"],
)

# Retrieval entropy gauge per tenant
LEARNING_RETRIEVAL_ENTROPY = get_gauge(
    "somabrain_learning_retrieval_entropy",
    "Entropy of retrieval weight distribution per tenant",
    labelnames=["tenant_id"],
)

# Regret KPIs (next-event + policy)
LEARNING_REGRET = get_histogram(
    "somabrain_learning_regret",
    "Regret distribution per tenant",
    labelnames=["tenant_id"],
    buckets=[i / 20.0 for i in range(0, 21)],
)
LEARNING_REGRET_EWMA = get_gauge(
    "somabrain_learning_regret_ewma",
    "EWMA regret per tenant",
    labelnames=["tenant_id"],
)

_regret_ema: dict[str, float] = {}
_REGRET_ALPHA = 0.15


def record_regret(tenant_id: str, regret: float) -> None:
    try:
        t = tenant_id or "public"
        r = max(0.0, min(1.0, float(regret)))
        LEARNING_REGRET.labels(tenant_id=t).observe(r)
        prev = _regret_ema.get(t)
        if prev is None:
            ema = r
        else:
            ema = _REGRET_ALPHA * r + (1.0 - _REGRET_ALPHA) * prev
        _regret_ema[t] = ema
        LEARNING_REGRET_EWMA.labels(tenant_id=t).set(ema)
    except Exception:
        pass


def update_learning_retrieval_entropy(tenant_id: str, entropy: float) -> None:
    try:
        LEARNING_RETRIEVAL_ENTROPY.labels(tenant_id=tenant_id).set(float(entropy))
    except Exception:
        pass


def record_learning_rollback(tenant_id: str):
    """Increment rollback counter for tenant."""
    LEARNING_ROLLBACKS.labels(tenant_id=tenant_id).inc()


def update_learning_wm_length(session_id: str, tenant_id: str, length: int):
    """Update working memory length metric for session/tenant."""
    LEARNING_WM_LENGTH.labels(session_id=session_id, tenant_id=tenant_id).set(length)


# Ensure tau_gauge for context builder is defined only once and shared across modules.
if "soma_context_builder_tau" in REGISTRY._names_to_collectors:
    tau_gauge = REGISTRY._names_to_collectors["soma_context_builder_tau"]
else:
    tau_gauge = Gauge(
        "soma_context_builder_tau",
        "Current tau value for diversity adaptation",
        ["tenant_id"],
        registry=REGISTRY,
    )


def mark_external_metric_scraped(source: str) -> None:
    """Mark an external exporter as scraped for readiness gating."""

    if not source:
        return
    label = str(source).strip().lower()
    if not label:
        return
    now = time.time()
    with _external_metrics_lock:
        _external_metrics_scraped[label] = now
    try:
        EXTERNAL_METRICS_SCRAPE_STATUS.labels(source=label).set(1)
    except Exception:
        pass


def external_metrics_ready(
    required: Iterable[str] | None = None, freshness_seconds: float | None = None
) -> bool:
    """Return True if all required exporters have reported a recent scrape."""

    targets = (
        [str(s).strip().lower() for s in required]
        if required is not None
        else list(_DEFAULT_EXTERNAL_METRICS)
    )
    now = time.time()
    with _external_metrics_lock:
        snapshot = dict(_external_metrics_scraped)
    for label in targets:
        if not label:
            continue
        ts = snapshot.get(label)
        if ts is None:
            return False
        if freshness_seconds is not None and now - ts > freshness_seconds:
            return False
    return True


def reset_external_metrics(sources: Iterable[str] | None = None) -> None:
    """Reset tracked scrape state for the provided sources (or all)."""

    if sources is None:
        with _external_metrics_lock:
            targets = list(_external_metrics_scraped.keys())
            _external_metrics_scraped.clear()
    else:
        targets = [str(s).strip().lower() for s in sources if str(s).strip()]
        with _external_metrics_lock:
            for label in targets:
                _external_metrics_scraped.pop(label, None)
    for label in targets:
        if not label:
            continue
        try:
            EXTERNAL_METRICS_SCRAPE_STATUS.labels(source=label).set(0)
        except Exception:
            pass


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


async def metrics_endpoint() -> Any:
    """
    FastAPI endpoint for exposing Prometheus metrics.

    Returns the current metrics in Prometheus exposition format.
    This endpoint can be scraped by Prometheus servers for monitoring.

    Returns:
        Response: FastAPI response with metrics data in Prometheus format.

    Example:
        >>> # Access via: GET /metrics
        >>> response = await metrics_endpoint()
        >>> print(response.media_type)  # 'text/plain; version=0.0.4; charset=utf-8'
    """
    # import Response locally to avoid hard dependency at module import time
    try:
        from fastapi import Response  # type: ignore
    except Exception:  # pragma: no cover - optional runtime dependency
        # If FastAPI isn't present, return raw bytes from the shared registry
        try:
            return generate_latest(registry)
        except Exception:
            return b""

    # Export only real counters from the shared registry – no synthetic increments.
    try:
        data = generate_latest(registry)
    except Exception:
        data = b""
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


async def timing_middleware(
    request: Any, call_next: Callable[[Any], Awaitable[Any]]
) -> Any:
    """
    FastAPI middleware for automatic request timing and metrics collection.

    Intercepts all HTTP requests to measure latency and count requests by method,
    path, and status code. Automatically updates Prometheus metrics.

    Args:
        request (Request): Incoming FastAPI request.
        call_next (Callable[[Request], Awaitable[Response]]): Next middleware/endpoint in chain.

    Returns:
        Response: The response from the next handler in the chain.

    Note:
        This middleware should be added to the FastAPI app middleware stack
        to enable automatic HTTP metrics collection.
    """
    start = time.perf_counter()
    response: Any | None = None
    try:
        response = await call_next(request)
        return response
    finally:
        elapsed = max(0.0, time.perf_counter() - start)
        path = request.url.path
        method = request.method
        HTTP_LATENCY.labels(method=method, path=path).observe(elapsed)
        status = getattr(
            response, "status_code", 500 if response is None else response.status_code
        )
        HTTP_COUNT.labels(method=method, path=path, status=str(status)).inc()


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
