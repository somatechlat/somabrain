"""Modular Metrics Package for SomaBrain.

Metrics are organized by domain in submodules. All metrics are re-exported
from this module for backward compatibility. For new code, prefer using
the interface module: from somabrain.metrics.interface import get_metrics
"""

from __future__ import annotations

# Export the interface module for dependency injection
from somabrain.metrics.interface import (
    MetricsInterface,
    NullMetrics,
    PrometheusMetrics,
    get_metrics,
    set_metrics,
    reset_metrics,
)

# Core infrastructure
from somabrain.metrics.core import (
    registry,
    Counter,
    Gauge,
    Histogram,
    Summary,
    get_counter,
    get_gauge,
    get_histogram,
    HTTP_COUNT,
    HTTP_LATENCY,
)

# Learning metrics
from somabrain.metrics.learning import (
    LEARNING_TAU,
    LEARNING_ENTROPY_CAP_HITS,
    LEARNING_RETRIEVAL_ALPHA,
    LEARNING_RETRIEVAL_BETA,
    LEARNING_RETRIEVAL_GAMMA,
    LEARNING_RETRIEVAL_TAU,
    LEARNING_UTILITY_LAMBDA,
    LEARNING_UTILITY_MU,
    LEARNING_UTILITY_NU,
    LEARNING_FEEDBACK_APPLIED,
    LEARNING_FEEDBACK_REJECTED,
    LEARNING_FEEDBACK_LATENCY,
    LEARNING_EFFECTIVE_LR,
    LEARNING_ROLLBACKS,
    LEARNING_WM_LENGTH,
    LEARNING_RETRIEVAL_ENTROPY,
    LEARNING_REGRET,
    LEARNING_REGRET_EWMA,
    LEARNER_LAG_SECONDS,
    tau_decay_events,
    tau_anneal_events,
    entropy_cap_events,
    update_learning_retrieval_weights,
    update_learning_utility_weights,
    update_learning_gains,
    update_learning_bounds,
    record_learning_feedback_applied,
    record_learning_feedback_rejected,
    record_learning_feedback_latency,
    update_learning_effective_lr,
    record_regret,
    update_learning_retrieval_entropy,
    record_learning_rollback,
    update_learning_wm_length,
)

# Memory metrics
from somabrain.metrics.memory_metrics import (
    WM_HITS,
    WM_MISSES,
    WM_ADMIT,
    WM_UTILIZATION,
    WM_EVICTIONS,
    RECALL_REQUESTS,
    RECALL_LATENCY,
    RETRIEVAL_REQUESTS,
    RETRIEVAL_LATENCY,
    RETRIEVAL_CANDIDATES,
    RETRIEVAL_PERSIST,
    RETRIEVAL_EMPTY,
    RETRIEVER_HITS,
    RETRIEVER_LATENCY,
    ANN_LATENCY,
    ANN_REBUILD_TOTAL,
    ANN_REBUILD_SECONDS,
    LTM_STORE_LAT,
    MEMORY_HTTP_REQUESTS,
    MEMORY_HTTP_LATENCY,
    HTTP_FAILURES,
    CIRCUIT_BREAKER_STATE,
    MEMORY_ITEMS,
    ETA_GAUGE,
    SPARSITY_GAUGE,
    MARGIN_MEAN,
    CONFIG_VERSION,
    CONTROLLER_CHANGES,
    MEMORY_OUTBOX_SYNC_TOTAL,
    record_memory_snapshot,
    observe_recall_latency,
    observe_ann_latency,
    mark_controller_change,
)

# Outbox metrics
from somabrain.metrics.outbox_metrics import (
    DEFAULT_TENANT_LABEL,
    OUTBOX_PENDING,
    OUTBOX_PROCESSED_TOTAL,
    OUTBOX_REPLAYED_TOTAL,
    CIRCUIT_STATE,
    report_outbox_pending,
    report_circuit_state,
    report_outbox_processed,
    report_outbox_replayed,
)

# Middleware
from somabrain.metrics.middleware import (
    EXTERNAL_METRICS_SCRAPE_STATUS,
    metrics_endpoint,
    PrometheusTimingMiddleware,
    mark_external_metric_scraped,
    external_metrics_ready,
    reset_external_metrics,
)

# OPA and Reward metrics
from somabrain.metrics.opa import (
    OPA_ALLOW_TOTAL,
    OPA_DENY_TOTAL,
    REWARD_ALLOW_TOTAL,
    REWARD_DENY_TOTAL,
)

# Constitution and Utility metrics
from somabrain.metrics.constitution import (
    CONSTITUTION_VERIFIED,
    CONSTITUTION_VERIFY_LATENCY,
    UTILITY_NEGATIVE,
    UTILITY_VALUE,
)

# Salience and Scorer metrics
from somabrain.metrics.salience import (
    SALIENCE_STORE,
    SALIENCE_HIST,
    SALIENCE_THRESH_STORE,
    SALIENCE_THRESH_ACT,
    SALIENCE_STORE_RATE_OBS,
    SALIENCE_ACT_RATE_OBS,
    FD_ENERGY_CAPTURE,
    FD_RESIDUAL,
    FD_TRACE_ERROR,
    FD_PSD_INVARIANT,
    SCORER_COMPONENT,
    SCORER_FINAL,
    SCORER_WEIGHT_CLAMPED,
)

# HRR and Unbind metrics
from somabrain.metrics.hrr import (
    HRR_CLEANUP_USED,
    HRR_CLEANUP_SCORE,
    HRR_CLEANUP_CALLS,
    HRR_ANCHOR_SIZE,
    HRR_CONTEXT_SAT,
    HRR_RERANK_APPLIED,
    HRR_RERANK_LTM_APPLIED,
    HRR_RERANK_WM_SKIPPED,
    UNBIND_PATH,
    UNBIND_WIENER_FLOOR,
    UNBIND_K_EST,
    UNBIND_SPECTRAL_BINS_CLAMPED,
    UNBIND_EPS_USED,
    RECONSTRUCTION_COSINE,
)

# Predictor and Planning metrics
from somabrain.metrics.predictor import (
    PREDICTOR_LATENCY,
    PREDICTOR_LATENCY_BY,
    PREDICTOR_ALTERNATIVE,
    PLANNING_LATENCY,
    PLANNING_LATENCY_P99,
    record_planning_latency,
)

# Re-export everything from the original metrics module for full backward compatibility
# This ensures existing imports continue to work (includes metrics not yet extracted)
# Neuromodulator metrics
from somabrain.metrics.neuromodulator import (
    NEUROMOD_DOPAMINE,
    NEUROMOD_SEROTONIN,
    NEUROMOD_NORADRENALINE,
    NEUROMOD_ACETYLCHOLINE,
    NEUROMOD_UPDATE_COUNT,
)

# Oak/Milvus metrics
from somabrain.metrics.oak import (
    OPTION_UTILITY_AVG,
    OPTION_COUNT,
    MILVUS_SEARCH_LAT_P95,
    MILVUS_INGEST_LAT_P95,
    MILVUS_SEGMENT_LOAD,
    MILVUS_UPSERT_RETRY_TOTAL,
    MILVUS_UPSERT_FAILURE_TOTAL,
    MILVUS_RECONCILE_MISSING,
    MILVUS_RECONCILE_ORPHAN,
)

# Consolidation and Supervisor metrics
from somabrain.metrics.consolidation import (
    CONSOLIDATION_RUNS,
    REPLAY_STRENGTH,
    REM_SYNTHESIZED,
    FREE_ENERGY,
    SUPERVISOR_MODULATION,
)

# Executive and Microcircuit metrics
from somabrain.metrics.executive import (
    EXEC_CONFLICT,
    EXEC_USE_GRAPH,
    EXEC_BANDIT_ARM,
    EXEC_BANDIT_REWARD,
    EXEC_K_SELECTED,
    MICRO_VOTE_ENTROPY,
    MICRO_COLUMN_ADMIT,
    MICRO_COLUMN_BEST,
    ATTENTION_LEVEL,
)

# Embedding and Index metrics
from somabrain.metrics.embedding import (
    EMBED_LAT,
    EMBED_CACHE_HIT,
    INDEX_PROFILE_USE,
    LINK_DECAY_PRUNED,
    AUDIT_KAFKA_PUBLISH,
)

# Recall quality and capacity metrics
from somabrain.metrics.recall_quality import (
    RECALL_MARGIN_TOP12,
    RECALL_SIM_TOP1,
    RECALL_SIM_TOPK_MEAN,
    RERANK_CONTRIB,
    DIVERSITY_PAIRWISE_MEAN,
    STORAGE_REDUCTION_RATIO,
    RATE_LIMITED_TOTAL,
    QUOTA_DENIED_TOTAL,
    QUOTA_RESETS,
    QUOTA_ADJUSTMENTS,
    RETRIEVAL_FUSION_APPLIED,
    RETRIEVAL_FUSION_SOURCES,
)

# Novelty and SDR metrics
from somabrain.metrics.novelty import (
    NOVELTY_RAW,
    ERROR_RAW,
    NOVELTY_NORM,
    ERROR_NORM,
    SDR_PREFILTER_LAT,
    SDR_CANDIDATES,
    RECALL_WM_LAT,
    RECALL_LTM_LAT,
    RECALL_CACHE_HIT,
    RECALL_CACHE_MISS,
)

# Segmentation and Fusion metrics
from somabrain.metrics.segmentation import (
    SEGMENTATION_BOUNDARIES_PER_HOUR,
    SEGMENTATION_DUPLICATE_RATIO,
    SEGMENTATION_HMM_STATE_VOLATILE,
    SEGMENTATION_MAX_DWELL_EXCEEDED,
    FUSION_WEIGHT_NORM_ERROR,
    FUSION_ALPHA_ADAPTIVE,
    FUSION_SOFTMAX_WEIGHT,
)

# Integration metrics (SB↔SFM) per H2.1-H2.5
from somabrain.metrics.integration import (
    SFM_REQUEST_TOTAL,
    SFM_REQUEST_DURATION,
    SFM_CIRCUIT_BREAKER_STATE,
    SFM_OUTBOX_PENDING,
    SFM_WM_PROMOTION_TOTAL,
    SFM_DEGRADATION_EVENTS,
    SFM_GRAPH_OPERATIONS,
    SFM_GRAPH_LATENCY,
    SFM_BULK_STORE_TOTAL,
    SFM_BULK_STORE_ITEMS,
    SFM_BULK_STORE_LATENCY,
    SFM_HYBRID_RECALL_TOTAL,
    SFM_HYBRID_RECALL_LATENCY,
    record_sfm_request,
    update_circuit_breaker_state,
    update_outbox_pending,
    record_wm_promotion,
    record_degradation_event,
    record_graph_operation,
    record_bulk_store,
    record_hybrid_recall,
)

# Legacy tau_gauge from core (to avoid circular imports)
from somabrain.metrics.core import tau_gauge, soma_next_event_regret  # noqa: F401

__all__ = [
    # Interface (for dependency injection)
    "MetricsInterface",
    "NullMetrics",
    "PrometheusMetrics",
    "get_metrics",
    "set_metrics",
    "reset_metrics",
    # Registry and factories
    "registry",
    "Counter",
    "Gauge",
    "Histogram",
    "Summary",
    "get_counter",
    "get_gauge",
    "get_histogram",
    # Core HTTP
    "HTTP_COUNT",
    "HTTP_LATENCY",
    "HTTP_FAILURES",
    # OPA and Reward
    "OPA_ALLOW_TOTAL",
    "OPA_DENY_TOTAL",
    "REWARD_ALLOW_TOTAL",
    "REWARD_DENY_TOTAL",
    # Memory
    "WM_HITS",
    "WM_MISSES",
    "WM_ADMIT",
    "WM_UTILIZATION",
    "WM_EVICTIONS",
    "MEMORY_ITEMS",
    "MEMORY_HTTP_REQUESTS",
    "MEMORY_HTTP_LATENCY",
    "RECALL_LATENCY",
    "RECALL_REQUESTS",
    "RETRIEVAL_REQUESTS",
    "RETRIEVAL_LATENCY",
    "RETRIEVAL_CANDIDATES",
    "RETRIEVAL_PERSIST",
    "RETRIEVAL_EMPTY",
    "RETRIEVER_HITS",
    "RETRIEVER_LATENCY",
    "ANN_LATENCY",
    "ANN_REBUILD_TOTAL",
    "ANN_REBUILD_SECONDS",
    "LTM_STORE_LAT",
    "MEMORY_OUTBOX_SYNC_TOTAL",
    "CIRCUIT_BREAKER_STATE",
    "ETA_GAUGE",
    "SPARSITY_GAUGE",
    "MARGIN_MEAN",
    "CONFIG_VERSION",
    "CONTROLLER_CHANGES",
    # Learning
    "LEARNING_TAU",
    "LEARNING_ENTROPY_CAP_HITS",
    "LEARNING_RETRIEVAL_ALPHA",
    "LEARNING_RETRIEVAL_BETA",
    "LEARNING_RETRIEVAL_GAMMA",
    "LEARNING_RETRIEVAL_TAU",
    "LEARNING_UTILITY_LAMBDA",
    "LEARNING_UTILITY_MU",
    "LEARNING_UTILITY_NU",
    "LEARNING_FEEDBACK_APPLIED",
    "LEARNING_FEEDBACK_REJECTED",
    "LEARNING_FEEDBACK_LATENCY",
    "LEARNING_EFFECTIVE_LR",
    "LEARNING_ROLLBACKS",
    "LEARNING_WM_LENGTH",
    "LEARNING_RETRIEVAL_ENTROPY",
    "LEARNING_REGRET",
    "LEARNING_REGRET_EWMA",
    "LEARNER_LAG_SECONDS",
    "tau_decay_events",
    "tau_anneal_events",
    "entropy_cap_events",
    "tau_gauge",
    # Neuromodulators
    "NEUROMOD_DOPAMINE",
    "NEUROMOD_SEROTONIN",
    "NEUROMOD_NORADRENALINE",
    "NEUROMOD_ACETYLCHOLINE",
    "NEUROMOD_UPDATE_COUNT",
    # Scorer/Salience
    "SCORER_COMPONENT",
    "SCORER_FINAL",
    "SCORER_WEIGHT_CLAMPED",
    "SALIENCE_HIST",
    "SALIENCE_STORE",
    "SALIENCE_THRESH_STORE",
    "SALIENCE_THRESH_ACT",
    "SALIENCE_STORE_RATE_OBS",
    "SALIENCE_ACT_RATE_OBS",
    "FD_ENERGY_CAPTURE",
    "FD_RESIDUAL",
    "FD_TRACE_ERROR",
    "FD_PSD_INVARIANT",
    # Predictor
    "PREDICTOR_LATENCY",
    "PREDICTOR_LATENCY_BY",
    "PREDICTOR_ALTERNATIVE",
    "PLANNING_LATENCY",
    "PLANNING_LATENCY_P99",
    # Oak/Milvus
    "OPTION_UTILITY_AVG",
    "OPTION_COUNT",
    "MILVUS_SEARCH_LAT_P95",
    "MILVUS_INGEST_LAT_P95",
    "MILVUS_SEGMENT_LOAD",
    "MILVUS_UPSERT_RETRY_TOTAL",
    "MILVUS_UPSERT_FAILURE_TOTAL",
    "MILVUS_RECONCILE_MISSING",
    "MILVUS_RECONCILE_ORPHAN",
    # Consolidation/Supervisor
    "CONSOLIDATION_RUNS",
    "REPLAY_STRENGTH",
    "REM_SYNTHESIZED",
    "FREE_ENERGY",
    "SUPERVISOR_MODULATION",
    # Executive/Microcircuit
    "EXEC_CONFLICT",
    "EXEC_USE_GRAPH",
    "EXEC_BANDIT_ARM",
    "EXEC_BANDIT_REWARD",
    "EXEC_K_SELECTED",
    "MICRO_VOTE_ENTROPY",
    "MICRO_COLUMN_ADMIT",
    "MICRO_COLUMN_BEST",
    "ATTENTION_LEVEL",
    # Embedding/Index
    "EMBED_LAT",
    "EMBED_CACHE_HIT",
    "INDEX_PROFILE_USE",
    "LINK_DECAY_PRUNED",
    "AUDIT_KAFKA_PUBLISH",
    # Recall quality
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
    # Novelty/SDR
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
    # Segmentation/Fusion
    "SEGMENTATION_BOUNDARIES_PER_HOUR",
    "SEGMENTATION_DUPLICATE_RATIO",
    "SEGMENTATION_HMM_STATE_VOLATILE",
    "SEGMENTATION_MAX_DWELL_EXCEEDED",
    "FUSION_WEIGHT_NORM_ERROR",
    "FUSION_ALPHA_ADAPTIVE",
    "FUSION_SOFTMAX_WEIGHT",
    # Outbox
    "DEFAULT_TENANT_LABEL",
    "OUTBOX_PENDING",
    "OUTBOX_PROCESSED_TOTAL",
    "OUTBOX_REPLAYED_TOTAL",
    "CIRCUIT_STATE",
    "report_outbox_pending",
    "report_circuit_state",
    "report_outbox_processed",
    "report_outbox_replayed",
    # Middleware
    "EXTERNAL_METRICS_SCRAPE_STATUS",
    # Constitution/Utility
    "CONSTITUTION_VERIFIED",
    "CONSTITUTION_VERIFY_LATENCY",
    "UTILITY_NEGATIVE",
    "UTILITY_VALUE",
    # HRR/Unbind
    "HRR_CLEANUP_USED",
    "HRR_CLEANUP_SCORE",
    "HRR_CLEANUP_CALLS",
    "HRR_ANCHOR_SIZE",
    "HRR_CONTEXT_SAT",
    "HRR_RERANK_APPLIED",
    "HRR_RERANK_LTM_APPLIED",
    "HRR_RERANK_WM_SKIPPED",
    "UNBIND_PATH",
    "UNBIND_WIENER_FLOOR",
    "UNBIND_K_EST",
    "UNBIND_SPECTRAL_BINS_CLAMPED",
    "UNBIND_EPS_USED",
    "RECONSTRUCTION_COSINE",
    # Functions
    "metrics_endpoint",
    "PrometheusTimingMiddleware",
    "update_learning_retrieval_weights",
    "update_learning_utility_weights",
    "update_learning_gains",
    "update_learning_bounds",
    "record_learning_feedback_applied",
    "record_learning_feedback_rejected",
    "record_learning_feedback_latency",
    "update_learning_effective_lr",
    "record_learning_rollback",
    "update_learning_wm_length",
    "update_learning_retrieval_entropy",
    "record_regret",
    "record_planning_latency",
    "record_memory_snapshot",
    "observe_recall_latency",
    "observe_ann_latency",
    "mark_controller_change",
    "mark_external_metric_scraped",
    "external_metrics_ready",
    "reset_external_metrics",
    # Integration metrics (SB↔SFM)
    "SFM_REQUEST_TOTAL",
    "SFM_REQUEST_DURATION",
    "SFM_CIRCUIT_BREAKER_STATE",
    "SFM_OUTBOX_PENDING",
    "SFM_WM_PROMOTION_TOTAL",
    "SFM_DEGRADATION_EVENTS",
    "SFM_GRAPH_OPERATIONS",
    "SFM_GRAPH_LATENCY",
    "SFM_BULK_STORE_TOTAL",
    "SFM_BULK_STORE_ITEMS",
    "SFM_BULK_STORE_LATENCY",
    "SFM_HYBRID_RECALL_TOTAL",
    "SFM_HYBRID_RECALL_LATENCY",
    "record_sfm_request",
    "update_circuit_breaker_state",
    "update_outbox_pending",
    "record_wm_promotion",
    "record_degradation_event",
    "record_graph_operation",
    "record_bulk_store",
    "record_hybrid_recall",
]
