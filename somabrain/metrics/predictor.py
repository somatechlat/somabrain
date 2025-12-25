"""Predictor and Planning Metrics for SomaBrain.

This module provides metrics for predictor latency tracking and
planning generation KPIs.

Metrics:
- PREDICTOR_LATENCY: Predictor call latency
- PREDICTOR_LATENCY_BY: Predictor call latency by provider
- PREDICTOR_ALTERNATIVE: Count of predictor timeouts/errors causing degrade
- PLANNING_LATENCY: Planning generation latency seconds
- PLANNING_LATENCY_P99: Approximate p99 planning latency seconds (rolling)

Functions:
- record_planning_latency: Record planning latency and update p99 gauge
"""

from __future__ import annotations

from somabrain.metrics.core import registry, Counter, Gauge, Histogram

# ---------------------------------------------------------------------------
# Predictor Metrics
# ---------------------------------------------------------------------------

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

PREDICTOR_ALTERNATIVE = Counter(
    "somabrain_predictor_alternative_total",
    "Count of predictor timeouts/errors causing degrade",
    registry=registry,
)

# ---------------------------------------------------------------------------
# Planning KPIs
# ---------------------------------------------------------------------------

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
    """Record planning latency and update rolling p99 gauge."""
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


__all__ = [
    "PREDICTOR_LATENCY",
    "PREDICTOR_LATENCY_BY",
    "PREDICTOR_ALTERNATIVE",
    "PLANNING_LATENCY",
    "PLANNING_LATENCY_P99",
    "record_planning_latency",
]
