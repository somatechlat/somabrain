"""Planning and FocusState Metrics for SomaBrain.

This module provides metrics for the Unified Planning Kernel and FocusState
integration, enabling observability for planning operations and focus tracking.

Metrics:
- PLAN_LATENCY: Planning operation latency by backend
- PLAN_EMPTY: Empty plan results with reason labels
- PLAN_GRAPH_UNAVAILABLE: Graph unavailable for planning
- FOCUS_UPDATE_LATENCY: Focus state update latency
- FOCUS_PERSIST: Focus snapshots persisted to memory
- PREDICT_COMPARE_MISSING_PREV: Prediction comparisons with missing previous focus

Requirements: 11.1, 11.2, 11.3, 11.4, 11.5
"""

from __future__ import annotations

from somabrain.metrics.core import Counter, Histogram, registry

# ---------------------------------------------------------------------------
# Planning Metrics
# ---------------------------------------------------------------------------

PLAN_LATENCY = Histogram(
    "somabrain_plan_latency_seconds",
    "Planning operation latency",
    ["backend"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
    registry=registry,
)

PLAN_EMPTY = Counter(
    "somabrain_plan_empty_total",
    "Empty plan results",
    ["reason"],
    registry=registry,
)

PLAN_GRAPH_UNAVAILABLE = Counter(
    "somabrain_plan_graph_unavailable_total",
    "Graph unavailable for planning",
    registry=registry,
)

# ---------------------------------------------------------------------------
# FocusState Metrics
# ---------------------------------------------------------------------------

FOCUS_UPDATE_LATENCY = Histogram(
    "somabrain_focus_update_latency_seconds",
    "Focus state update latency",
    buckets=[0.0001, 0.0005, 0.001, 0.005, 0.01, 0.025, 0.05],
    registry=registry,
)

FOCUS_PERSIST = Counter(
    "somabrain_focus_persist_total",
    "Focus snapshots persisted to memory",
    registry=registry,
)

# ---------------------------------------------------------------------------
# Predictor Metrics
# ---------------------------------------------------------------------------

PREDICT_COMPARE_MISSING_PREV = Counter(
    "somabrain_predict_compare_missing_prev_total",
    "Prediction comparisons with missing previous focus",
    registry=registry,
)

__all__ = [
    # Planning
    "PLAN_LATENCY",
    "PLAN_EMPTY",
    "PLAN_GRAPH_UNAVAILABLE",
    # FocusState
    "FOCUS_UPDATE_LATENCY",
    "FOCUS_PERSIST",
    # Predictor
    "PREDICT_COMPARE_MISSING_PREV",
]
