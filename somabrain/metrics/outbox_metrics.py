"""Outbox and Circuit Breaker Metrics for SomaBrain.

This module contains metrics related to the outbox pattern and circuit breaker:
- Outbox pending/processed/replayed counters
- Circuit breaker state gauges
- Feature flag toggles

Helper functions for reporting outbox state are also provided.
"""

from __future__ import annotations

from somabrain.metrics.core import (
    _counter,
    _gauge,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_TENANT_LABEL = "default"


def _normalize_tenant_label(tenant_id: str | None) -> str:
    """Normalize tenant ID for metric labels."""
    if not tenant_id:
        return DEFAULT_TENANT_LABEL
    return str(tenant_id)


# ---------------------------------------------------------------------------
# Outbox Metrics
# ---------------------------------------------------------------------------

OUTBOX_PENDING = _gauge(
    "memory_outbox_pending",
    "Number of pending messages in the out-box queue",
    ["tenant_id"],
)

OUTBOX_REPLAY_TRIGGERED = _counter(
    "memory_outbox_replay_total",
    "Admin-triggered outbox replays partitioned by outcome.",
    ["result"],
)

OUTBOX_FAILED_TOTAL = _counter(
    "memory_outbox_failed_seen_total",
    "Count of failed outbox events observed via admin API endpoints.",
    ["tenant_id"],
)

OUTBOX_PROCESSED_TOTAL = _counter(
    "somabrain_outbox_processed_total",
    "Total number of outbox events successfully published to Kafka",
    ["tenant_id", "topic"],
)

OUTBOX_REPLAYED_TOTAL = _counter(
    "somabrain_outbox_replayed_total",
    "Total number of outbox events marked for replay",
    ["tenant_id"],
)


# ---------------------------------------------------------------------------
# Circuit Breaker Metrics
# ---------------------------------------------------------------------------

CIRCUIT_STATE = _gauge(
    "memory_circuit_state",
    "Circuit breaker state for external memory service: 0=closed, 1=open",
    ["tenant_id"],
)


# ---------------------------------------------------------------------------
# Feature Flag Metrics
# ---------------------------------------------------------------------------

FEATURE_FLAG_TOGGLE_TOTAL = _counter(
    "somabrain_feature_flag_toggle_total",
    "Number of feature flag toggles grouped by action.",
    ["action"],
)


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def report_outbox_pending(tenant_id: str | None, count: int) -> None:
    """Report the number of pending outbox messages for a tenant."""
    try:
        OUTBOX_PENDING.labels(tenant_id=_normalize_tenant_label(tenant_id)).set(count)
    except Exception:
        pass


def report_circuit_state(tenant_id: str | None, is_open: bool) -> None:
    """Report the circuit breaker state for a tenant."""
    try:
        CIRCUIT_STATE.labels(tenant_id=_normalize_tenant_label(tenant_id)).set(
            1 if is_open else 0
        )
    except Exception:
        pass


def report_outbox_processed(tenant_id: str | None, topic: str, count: int = 1) -> None:
    """Report outbox events successfully processed to Kafka."""
    try:
        OUTBOX_PROCESSED_TOTAL.labels(
            tenant_id=_normalize_tenant_label(tenant_id),
            topic=str(topic),
        ).inc(max(0, int(count)))
    except Exception:
        pass


def report_outbox_replayed(tenant_id: str | None, count: int = 1) -> None:
    """Report outbox events marked for replay."""
    try:
        OUTBOX_REPLAYED_TOTAL.labels(tenant_id=_normalize_tenant_label(tenant_id)).inc(
            max(0, int(count))
        )
    except Exception:
        pass


__all__ = [
    # Constants
    "DEFAULT_TENANT_LABEL",
    "_normalize_tenant_label",
    # Outbox metrics
    "OUTBOX_PENDING",
    "OUTBOX_REPLAY_TRIGGERED",
    "OUTBOX_FAILED_TOTAL",
    "OUTBOX_PROCESSED_TOTAL",
    "OUTBOX_REPLAYED_TOTAL",
    # Circuit breaker
    "CIRCUIT_STATE",
    # Feature flags
    "FEATURE_FLAG_TOGGLE_TOTAL",
    # Helper functions
    "report_outbox_pending",
    "report_circuit_state",
    "report_outbox_processed",
    "report_outbox_replayed",
]
