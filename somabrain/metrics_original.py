"""
Metrics Module for SomaBrain (Re-export Layer).

This module provides backward compatibility for imports from somabrain.metrics_original.
All metrics have been decomposed into domain-specific modules under somabrain/metrics/.

For new code, import directly from somabrain.metrics:
    from somabrain.metrics import HTTP_COUNT, WM_HITS, ...

Domain modules:
- somabrain.metrics.core: Registry, factory functions, HTTP metrics
- somabrain.metrics.learning: Adaptation, tau, entropy metrics
- somabrain.metrics.memory_metrics: WM, LTM, retrieval, ANN metrics
- somabrain.metrics.outbox_metrics: Outbox and circuit breaker metrics
- somabrain.metrics.middleware: FastAPI integration
- somabrain.metrics.opa: OPA/Reward metrics
- somabrain.metrics.constitution: Constitution/Utility metrics
- somabrain.metrics.salience: Salience/Scorer/FD metrics
- somabrain.metrics.hrr: HRR/Unbind metrics
- somabrain.metrics.predictor: Predictor/Planning metrics
- somabrain.metrics.neuromodulator: Neuromodulator metrics
- somabrain.metrics.oak: Oak/Milvus metrics
- somabrain.metrics.consolidation: Consolidation/Supervisor metrics
- somabrain.metrics.executive: Executive/Microcircuit metrics
- somabrain.metrics.embedding: Embedding/Index metrics
- somabrain.metrics.recall_quality: Recall quality/Capacity metrics
- somabrain.metrics.novelty: Novelty/SDR metrics
- somabrain.metrics.segmentation: Segmentation/Fusion metrics
"""

from __future__ import annotations

# Re-export from core
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

# Re-export from learning
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
    LEARNING_GAIN,
    LEARNING_BOUND,
    LEARNER_EVENTS_CONSUMED,
    LEARNER_EVENTS_PRODUCED,
    LEARNER_EVENTS_FAILED,
    LEARNER_EVENT_LATENCY,
    LEARNER_DLQ_TOTAL,
    LEARNING_EXPERIMENT_ACTIVE,
    LEARNING_EXPERIMENT_PROMOTIONS,
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

# Re-export from memory_metrics
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

# Re-export from outbox_metrics
from somabrain.metrics.outbox_metrics import (
    OUTBOX_PENDING,
    OUTBOX_PROCESSED_TOTAL,
    OUTBOX_REPLAYED_TOTAL,
    OUTBOX_REPLAY_TRIGGERED,
    OUTBOX_FAILED_TOTAL,
    CIRCUIT_STATE,
    FEATURE_FLAG_TOGGLE_TOTAL,
    DEFAULT_TENANT_LABEL,
    report_outbox_pending,
    report_circuit_state,
    report_outbox_processed,
    report_outbox_replayed,
)

# Re-export from middleware
from somabrain.metrics.middleware import (
    EXTERNAL_METRICS_SCRAPE_STATUS,
    metrics_endpoint,
    timing_middleware,
    mark_external_metric_scraped,
    external_metrics_ready,
    reset_external_metrics,
)

# Re-export from opa
from somabrain.metrics.opa import (
    OPA_ALLOW_TOTAL,
    OPA_DENY_TOTAL,
    REWARD_ALLOW_TOTAL,
    REWARD_DENY_TOTAL,
)

# Re-export from constitution
from somabrain.metrics.constitution import (
    CONSTITUTION_VERIFIED,
    CONSTITUTION_VERIFY_LATENCY,
    UTILITY_NEGATIVE,
    UTILITY_VALUE,
)

# Re-export from salience
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

# Re-export from hrr
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

# Re-export from predictor
from somabrain.metrics.predictor import (
    PREDICTOR_LATENCY,
    PREDICTOR_LATENCY_BY,
    PREDICTOR_ALTERNATIVE,
    PLANNING_LATENCY,
    PLANNING_LATENCY_P99,
    record_planning_latency,
)

# Re-export from neuromodulator
from somabrain.metrics.neuromodulator import (
    NEUROMOD_DOPAMINE,
    NEUROMOD_SEROTONIN,
    NEUROMOD_NORADRENALINE,
    NEUROMOD_ACETYLCHOLINE,
    NEUROMOD_UPDATE_COUNT,
)

# Re-export from oak
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

# Re-export from consolidation
from somabrain.metrics.consolidation import (
    CONSOLIDATION_RUNS,
    REPLAY_STRENGTH,
    REM_SYNTHESIZED,
    FREE_ENERGY,
    SUPERVISOR_MODULATION,
)

# Re-export from executive
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

# Re-export from embedding
from somabrain.metrics.embedding import (
    EMBED_LAT,
    EMBED_CACHE_HIT,
    INDEX_PROFILE_USE,
    LINK_DECAY_PRUNED,
    AUDIT_KAFKA_PUBLISH,
)

# Re-export from recall_quality
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

# Re-export from novelty
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

# Re-export from segmentation
from somabrain.metrics.segmentation import (
    SEGMENTATION_BOUNDARIES_PER_HOUR,
    SEGMENTATION_DUPLICATE_RATIO,
    SEGMENTATION_HMM_STATE_VOLATILE,
    SEGMENTATION_MAX_DWELL_EXCEEDED,
    FUSION_WEIGHT_NORM_ERROR,
    FUSION_ALPHA_ADAPTIVE,
    FUSION_SOFTMAX_WEIGHT,
)

# Legacy gauges from core (to avoid circular imports)
from somabrain.metrics.core import tau_gauge, soma_next_event_regret

__all__ = [
    # Core
    "registry",
    "Counter",
    "Gauge",
    "Histogram",
    "Summary",
    "get_counter",
    "get_gauge",
    "get_histogram",
    "HTTP_COUNT",
    "HTTP_LATENCY",
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
    "soma_next_event_regret",
    # Memory
    "WM_HITS",
    "WM_MISSES",
    "WM_ADMIT",
    "WM_UTILIZATION",
    "WM_EVICTIONS",
    "MEMORY_ITEMS",
    "RECALL_LATENCY",
    "RECALL_REQUESTS",
    "RETRIEVAL_REQUESTS",
    "RETRIEVAL_LATENCY",
    "RETRIEVAL_CANDIDATES",
    "ANN_LATENCY",
    "LTM_STORE_LAT",
    "HTTP_FAILURES",
    "CIRCUIT_BREAKER_STATE",
    # OPA
    "OPA_ALLOW_TOTAL",
    "OPA_DENY_TOTAL",
    "REWARD_ALLOW_TOTAL",
    "REWARD_DENY_TOTAL",
    # Constitution
    "CONSTITUTION_VERIFIED",
    "CONSTITUTION_VERIFY_LATENCY",
    "UTILITY_NEGATIVE",
    "UTILITY_VALUE",
    # Salience
    "SALIENCE_STORE",
    "SALIENCE_HIST",
    "SCORER_COMPONENT",
    "SCORER_FINAL",
    # HRR
    "HRR_CLEANUP_USED",
    "HRR_CLEANUP_SCORE",
    "HRR_RERANK_APPLIED",
    "UNBIND_PATH",
    "RECONSTRUCTION_COSINE",
    # Predictor
    "PREDICTOR_LATENCY",
    "PREDICTOR_LATENCY_BY",
    "PREDICTOR_ALTERNATIVE",
    "PLANNING_LATENCY",
    # Neuromodulator
    "NEUROMOD_DOPAMINE",
    "NEUROMOD_SEROTONIN",
    "NEUROMOD_NORADRENALINE",
    "NEUROMOD_ACETYLCHOLINE",
    # Oak/Milvus
    "OPTION_UTILITY_AVG",
    "OPTION_COUNT",
    "MILVUS_SEARCH_LAT_P95",
    "MILVUS_INGEST_LAT_P95",
    # Consolidation
    "CONSOLIDATION_RUNS",
    "REPLAY_STRENGTH",
    "REM_SYNTHESIZED",
    "FREE_ENERGY",
    "SUPERVISOR_MODULATION",
    # Executive
    "EXEC_CONFLICT",
    "EXEC_USE_GRAPH",
    "EXEC_BANDIT_ARM",
    "EXEC_BANDIT_REWARD",
    "EXEC_K_SELECTED",
    "MICRO_VOTE_ENTROPY",
    "MICRO_COLUMN_ADMIT",
    "MICRO_COLUMN_BEST",
    "ATTENTION_LEVEL",
    # Embedding
    "EMBED_LAT",
    "EMBED_CACHE_HIT",
    "INDEX_PROFILE_USE",
    "AUDIT_KAFKA_PUBLISH",
    # Recall quality
    "RECALL_MARGIN_TOP12",
    "RATE_LIMITED_TOTAL",
    "QUOTA_DENIED_TOTAL",
    "QUOTA_RESETS",
    "QUOTA_ADJUSTMENTS",
    # Novelty
    "NOVELTY_RAW",
    "ERROR_RAW",
    "NOVELTY_NORM",
    "ERROR_NORM",
    "SDR_PREFILTER_LAT",
    "SDR_CANDIDATES",
    # Segmentation
    "SEGMENTATION_BOUNDARIES_PER_HOUR",
    "SEGMENTATION_DUPLICATE_RATIO",
    "SEGMENTATION_HMM_STATE_VOLATILE",
    "SEGMENTATION_MAX_DWELL_EXCEEDED",
    "FUSION_WEIGHT_NORM_ERROR",
    "FUSION_ALPHA_ADAPTIVE",
    "FUSION_SOFTMAX_WEIGHT",
    # Outbox
    "OUTBOX_PENDING",
    "CIRCUIT_STATE",
    "report_outbox_pending",
    "report_circuit_state",
    "report_outbox_processed",
    "report_outbox_replayed",
    # Functions
    "metrics_endpoint",
    "timing_middleware",
    "update_learning_retrieval_weights",
    "update_learning_utility_weights",
    "record_learning_feedback_applied",
    "record_learning_feedback_rejected",
    "record_learning_feedback_latency",
    "update_learning_effective_lr",
    "record_learning_rollback",
    "record_regret",
    "record_planning_latency",
    "record_memory_snapshot",
    "observe_recall_latency",
    "observe_ann_latency",
    "mark_controller_change",
    "mark_external_metric_scraped",
    "external_metrics_ready",
    "reset_external_metrics",
]
