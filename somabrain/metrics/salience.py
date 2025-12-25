"""Salience and Scorer Metrics for SomaBrain.

This module provides metrics for salience scoring, FD (Frequent Directions)
sketch monitoring, and unified scorer component tracking.

Metrics:
- SALIENCE_STORE: Stores gated by salience
- SALIENCE_HIST: Salience score distribution
- SALIENCE_THRESH_STORE: Current store threshold
- SALIENCE_THRESH_ACT: Current act threshold
- SALIENCE_STORE_RATE_OBS: Observed EWMA store rate
- SALIENCE_ACT_RATE_OBS: Observed EWMA act rate
- FD_ENERGY_CAPTURE: FD salience sketch energy capture ratio
- FD_RESIDUAL: Residual energy ratio per vector for FD salience
- FD_TRACE_ERROR: Trace normalization error for FD sketch
- FD_PSD_INVARIANT: PSD invariant flag for FD sketch
- SCORER_COMPONENT: Unified scorer component values
- SCORER_FINAL: Unified scorer combined score
- SCORER_WEIGHT_CLAMPED: Unified scorer weight clamp events
"""

from __future__ import annotations

from somabrain.metrics.core import registry, Counter, Gauge, Histogram

# ---------------------------------------------------------------------------
# Salience Metrics
# ---------------------------------------------------------------------------

SALIENCE_STORE = Counter(
    "somabrain_store_events_total",
    "Stores gated by salience",
    registry=registry,
)

SALIENCE_HIST = Histogram(
    "somabrain_salience_score",
    "Salience score distribution",
    buckets=[i / 20.0 for i in range(0, 21)],
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

# ---------------------------------------------------------------------------
# FD (Frequent Directions) Sketch Metrics
# ---------------------------------------------------------------------------

FD_ENERGY_CAPTURE = Gauge(
    "somabrain_fd_energy_capture_ratio",
    "FD salience sketch energy capture ratio",
    registry=registry,
)

FD_RESIDUAL = Histogram(
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

# ---------------------------------------------------------------------------
# Unified Scorer Metrics
# ---------------------------------------------------------------------------

SCORER_COMPONENT = Histogram(
    "somabrain_scorer_component",
    "Unified scorer component values",
    ["component"],
    buckets=[i / 10.0 for i in range(-10, 11)],
    registry=registry,
)

SCORER_FINAL = Histogram(
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

__all__ = [
    # Salience
    "SALIENCE_STORE",
    "SALIENCE_HIST",
    "SALIENCE_THRESH_STORE",
    "SALIENCE_THRESH_ACT",
    "SALIENCE_STORE_RATE_OBS",
    "SALIENCE_ACT_RATE_OBS",
    # FD Sketch
    "FD_ENERGY_CAPTURE",
    "FD_RESIDUAL",
    "FD_TRACE_ERROR",
    "FD_PSD_INVARIANT",
    # Scorer
    "SCORER_COMPONENT",
    "SCORER_FINAL",
    "SCORER_WEIGHT_CLAMPED",
]
