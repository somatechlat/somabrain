from __future__ import annotations

from typing import Callable
import time
from fastapi import Request, Response
from prometheus_client import Counter, Histogram, Gauge, CollectorRegistry, CONTENT_TYPE_LATEST, generate_latest


registry = CollectorRegistry()

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
WM_HITS = Counter("somabrain_wm_hits_total", "WM recall hits", registry=registry)
WM_MISSES = Counter("somabrain_wm_misses_total", "WM recall misses", registry=registry)
SALIENCE_STORE = Counter("somabrain_store_events_total", "Stores gated by salience", registry=registry)
from prometheus_client import Histogram as _Hist
SALIENCE_HIST = _Hist("somabrain_salience_score", "Salience score distribution", buckets=[i/20.0 for i in range(0,21)], registry=registry)

# HRR cleanup metrics
HRR_CLEANUP_USED = Counter("somabrain_hrr_cleanup_used_total", "Times HRR cleanup was applied", registry=registry)
HRR_CLEANUP_SCORE = _Hist(
    "somabrain_hrr_cleanup_score",
    "HRR cleanup top-1 cosine score",
    buckets=[i/20.0 for i in range(0,21)],
    registry=registry,
)
from prometheus_client import Counter as _PC
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
    buckets=[i/20.0 for i in range(0,21)],
    registry=registry,
)

# Phase 0 — A/B + stage metrics
from prometheus_client import Histogram as _PHist
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
from prometheus_client import Counter as _PCounter
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
    buckets=[i/20.0 for i in range(0,21)],
    labelnames=["cohort"],
    registry=registry,
)
ERROR_RAW = _Hist(
    "somabrain_error_raw",
    "Prediction error raw distribution",
    buckets=[i/20.0 for i in range(0,21)],
    labelnames=["cohort"],
    registry=registry,
)
NOVELTY_NORM = _Hist(
    "somabrain_novelty_norm",
    "Novelty normalized (z-score) distribution",
    buckets=[-5 + i*0.5 for i in range(0,21)],
    labelnames=["cohort"],
    registry=registry,
)
ERROR_NORM = _Hist(
    "somabrain_error_norm",
    "Prediction error normalized (z-score) distribution",
    buckets=[-5 + i*0.5 for i in range(0,21)],
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


async def metrics_endpoint() -> Response:
    data = generate_latest(registry)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


async def timing_middleware(request: Request, call_next: Callable[[Request], Response]) -> Response:
    start = time.perf_counter()
    response: Response | None = None
    try:
        response = await call_next(request)
        return response
    finally:
        elapsed = max(0.0, time.perf_counter() - start)
        path = request.url.path
        method = request.method
        HTTP_LATENCY.labels(method=method, path=path).observe(elapsed)
        status = getattr(response, "status_code", 500 if response is None else response.status_code)
        HTTP_COUNT.labels(method=method, path=path, status=str(status)).inc()
