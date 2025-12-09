"""Modular Metrics Package for SomaBrain.

This package provides comprehensive metrics collection and monitoring using
Prometheus client library. Metrics are organized by domain:

- core.py: HTTP, health, and system-level metrics
- memory.py: Memory operation metrics (WM, LTM, retrieval)
- learning.py: Adaptation, tau, entropy, neuromodulator metrics
- scorer.py: Scorer component metrics

All metrics are re-exported from this module for backward compatibility:
    from somabrain.metrics import HTTP_COUNT, WM_HITS, ...
"""

from __future__ import annotations

# Re-export everything from the original metrics module for backward compatibility
# This ensures existing imports continue to work
from somabrain.metrics_original import *  # noqa: F401, F403

# Also explicitly export key items for IDE support
from somabrain.metrics_original import (
    # Registry and helpers
    registry,
    Counter,
    Gauge,
    Histogram,
    Summary,
    get_counter,
    get_gauge,
    get_histogram,
    # Core HTTP metrics
    HTTP_COUNT,
    HTTP_LATENCY,
    HTTP_FAILURES,
    # OPA metrics
    OPA_ALLOW_TOTAL,
    OPA_DENY_TOTAL,
    # Memory metrics
    WM_HITS,
    WM_MISSES,
    WM_ADMIT,
    WM_UTILIZATION,
    WM_EVICTIONS,
    MEMORY_ITEMS,
    MEMORY_HTTP_REQUESTS,
    MEMORY_HTTP_LATENCY,
    RECALL_LATENCY,
    RECALL_REQUESTS,
    RETRIEVAL_REQUESTS,
    RETRIEVAL_LATENCY,
    RETRIEVAL_CANDIDATES,
    # Learning metrics
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
    tau_decay_events,
    tau_anneal_events,
    entropy_cap_events,
    # Neuromodulator metrics
    NEUROMOD_DOPAMINE,
    NEUROMOD_SEROTONIN,
    NEUROMOD_NORADRENALINE,
    NEUROMOD_ACETYLCHOLINE,
    NEUROMOD_UPDATE_COUNT,
    # Scorer metrics
    SCORER_COMPONENT,
    SCORER_FINAL,
    SCORER_WEIGHT_CLAMPED,
    SALIENCE_HIST,
    SALIENCE_STORE,
    # Predictor metrics
    PREDICTOR_LATENCY,
    PREDICTOR_LATENCY_BY,
    PREDICTOR_ALTERNATIVE,
    # Oak/Milvus metrics
    OPTION_UTILITY_AVG,
    OPTION_COUNT,
    MILVUS_SEARCH_LAT_P95,
    MILVUS_INGEST_LAT_P95,
    # Consolidation metrics
    CONSOLIDATION_RUNS,
    REPLAY_STRENGTH,
    REM_SYNTHESIZED,
    # Helper functions
    metrics_endpoint,
    timing_middleware,
    update_learning_retrieval_weights,
    update_learning_utility_weights,
    record_learning_feedback_applied,
    record_learning_feedback_rejected,
    record_learning_feedback_latency,
    update_learning_effective_lr,
    record_learning_rollback,
    record_regret,
    record_planning_latency,
    record_memory_snapshot,
    observe_recall_latency,
    observe_ann_latency,
    mark_controller_change,
    mark_external_metric_scraped,
    external_metrics_ready,
    reset_external_metrics,
    report_outbox_pending,
    report_circuit_state,
    report_outbox_processed,
    report_outbox_replayed,
)

__all__ = [
    # Registry
    "registry",
    "Counter",
    "Gauge",
    "Histogram",
    "Summary",
    "get_counter",
    "get_gauge",
    "get_histogram",
    # Core
    "HTTP_COUNT",
    "HTTP_LATENCY",
    "HTTP_FAILURES",
    "OPA_ALLOW_TOTAL",
    "OPA_DENY_TOTAL",
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
    "tau_decay_events",
    "tau_anneal_events",
    "entropy_cap_events",
    # Neuromodulators
    "NEUROMOD_DOPAMINE",
    "NEUROMOD_SEROTONIN",
    "NEUROMOD_NORADRENALINE",
    "NEUROMOD_ACETYLCHOLINE",
    "NEUROMOD_UPDATE_COUNT",
    # Scorer
    "SCORER_COMPONENT",
    "SCORER_FINAL",
    "SCORER_WEIGHT_CLAMPED",
    "SALIENCE_HIST",
    "SALIENCE_STORE",
    # Predictor
    "PREDICTOR_LATENCY",
    "PREDICTOR_LATENCY_BY",
    "PREDICTOR_ALTERNATIVE",
    # Oak/Milvus
    "OPTION_UTILITY_AVG",
    "OPTION_COUNT",
    "MILVUS_SEARCH_LAT_P95",
    "MILVUS_INGEST_LAT_P95",
    # Consolidation
    "CONSOLIDATION_RUNS",
    "REPLAY_STRENGTH",
    "REM_SYNTHESIZED",
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
    "report_outbox_pending",
    "report_circuit_state",
    "report_outbox_processed",
    "report_outbox_replayed",
]
