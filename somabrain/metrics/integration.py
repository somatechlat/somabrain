"""Integration Metrics for SB↔SFM Communication.

Per Requirements H2.1-H2.5:
- H2.1: SFM_REQUEST_TOTAL counter with operation, tenant, status labels
- H2.2: SFM_REQUEST_DURATION histogram with operation, tenant labels
- H2.3: CIRCUIT_BREAKER_STATE gauge with tenant label
- H2.4: OUTBOX_PENDING gauge with tenant label
- H2.5: WM_PROMOTION_TOTAL counter with tenant label

This module provides Prometheus metrics for monitoring the SomaBrain to
SomaFractalMemory integration layer, including request counts, latencies,
circuit breaker states, and outbox queue depths.
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

from somabrain.metrics.core import registry

# H2.1: SFM request counter with operation, tenant, status labels
SFM_REQUEST_TOTAL = Counter(
    "sb_sfm_request_total",
    "Total requests from SomaBrain to SomaFractalMemory",
    ["operation", "tenant", "status"],
    registry=registry,
)

# H2.2: SFM request duration histogram with operation, tenant labels
SFM_REQUEST_DURATION = Histogram(
    "sb_sfm_request_duration_seconds",
    "Request duration from SomaBrain to SomaFractalMemory",
    ["operation", "tenant"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=registry,
)

# H2.3: Circuit breaker state gauge (0=closed, 1=half-open, 2=open)
SFM_CIRCUIT_BREAKER_STATE = Gauge(
    "sb_sfm_circuit_breaker_state",
    "Circuit breaker state for SFM calls (0=closed, 1=half-open, 2=open)",
    ["tenant"],
    registry=registry,
)

# H2.4: Outbox pending events gauge per tenant
SFM_OUTBOX_PENDING = Gauge(
    "sb_sfm_outbox_pending_total",
    "Pending outbox events for SFM operations",
    ["tenant"],
    registry=registry,
)

# H2.5: WM to LTM promotion counter
SFM_WM_PROMOTION_TOTAL = Counter(
    "sb_sfm_wm_promotion_total",
    "Total WM to LTM promotions via SFM",
    ["tenant", "status"],
    registry=registry,
)

# Additional integration metrics for comprehensive monitoring

# Degradation mode tracking
SFM_DEGRADATION_EVENTS = Counter(
    "sb_sfm_degradation_events_total",
    "Total degradation mode events (enter/exit)",
    ["tenant", "event_type"],
    registry=registry,
)

# Graph operation metrics
SFM_GRAPH_OPERATIONS = Counter(
    "sb_sfm_graph_operations_total",
    "Total graph operations via SFM",
    ["tenant", "operation", "status"],
    registry=registry,
)

SFM_GRAPH_LATENCY = Histogram(
    "sb_sfm_graph_latency_seconds",
    "Graph operation latency via SFM",
    ["tenant", "operation"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
    registry=registry,
)

# Bulk operation metrics
SFM_BULK_STORE_TOTAL = Counter(
    "sb_sfm_bulk_store_total",
    "Total bulk store operations to SFM",
    ["tenant", "status"],
    registry=registry,
)

SFM_BULK_STORE_ITEMS = Counter(
    "sb_sfm_bulk_store_items_total",
    "Total items in bulk store operations",
    ["tenant", "status"],
    registry=registry,
)

SFM_BULK_STORE_LATENCY = Histogram(
    "sb_sfm_bulk_store_latency_seconds",
    "Bulk store operation latency",
    ["tenant"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
    registry=registry,
)

# Hybrid recall metrics
SFM_HYBRID_RECALL_TOTAL = Counter(
    "sb_sfm_hybrid_recall_total",
    "Total hybrid recall operations",
    ["tenant", "status", "fallback"],
    registry=registry,
)

SFM_HYBRID_RECALL_LATENCY = Histogram(
    "sb_sfm_hybrid_recall_latency_seconds",
    "Hybrid recall operation latency",
    ["tenant"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
    registry=registry,
)


def record_sfm_request(
    operation: str,
    tenant: str,
    status: str,
    duration_seconds: float,
) -> None:
    """Record an SFM request with metrics.

    Per Requirements H2.1, H2.2.

    Args:
        operation: Operation type (e.g., 'remember', 'recall', 'graph_link')
        tenant: Tenant identifier
        status: Request status ('success', 'error', 'timeout')
        duration_seconds: Request duration in seconds
    """
    SFM_REQUEST_TOTAL.labels(operation=operation, tenant=tenant, status=status).inc()
    SFM_REQUEST_DURATION.labels(operation=operation, tenant=tenant).observe(
        duration_seconds
    )


def update_circuit_breaker_state(tenant: str, state: int) -> None:
    """Update circuit breaker state gauge.

    Per Requirement H2.3.

    Args:
        tenant: Tenant identifier
        state: Circuit state (0=closed, 1=half-open, 2=open)
    """
    SFM_CIRCUIT_BREAKER_STATE.labels(tenant=tenant).set(state)


def update_outbox_pending(tenant: str, count: int) -> None:
    """Update outbox pending count gauge.

    Per Requirement H2.4.

    Args:
        tenant: Tenant identifier
        count: Number of pending outbox events
    """
    SFM_OUTBOX_PENDING.labels(tenant=tenant).set(count)


def record_wm_promotion(tenant: str, status: str) -> None:
    """Record a WM to LTM promotion event.

    Per Requirement H2.5.

    Args:
        tenant: Tenant identifier
        status: Promotion status ('success', 'error', 'queued')
    """
    SFM_WM_PROMOTION_TOTAL.labels(tenant=tenant, status=status).inc()


def record_degradation_event(tenant: str, event_type: str) -> None:
    """Record a degradation mode event.

    Args:
        tenant: Tenant identifier
        event_type: Event type ('enter', 'exit', 'alert')
    """
    SFM_DEGRADATION_EVENTS.labels(tenant=tenant, event_type=event_type).inc()


def record_graph_operation(
    tenant: str,
    operation: str,
    status: str,
    duration_seconds: float,
) -> None:
    """Record a graph operation with metrics.

    Args:
        tenant: Tenant identifier
        operation: Operation type ('link', 'neighbors', 'path')
        status: Operation status ('success', 'error', 'timeout')
        duration_seconds: Operation duration in seconds
    """
    SFM_GRAPH_OPERATIONS.labels(tenant=tenant, operation=operation, status=status).inc()
    SFM_GRAPH_LATENCY.labels(tenant=tenant, operation=operation).observe(
        duration_seconds
    )


def record_bulk_store(
    tenant: str,
    status: str,
    succeeded: int,
    failed: int,
    duration_seconds: float,
) -> None:
    """Record a bulk store operation with metrics.

    Args:
        tenant: Tenant identifier
        status: Overall operation status ('success', 'partial', 'error')
        succeeded: Number of items successfully stored
        failed: Number of items that failed
        duration_seconds: Operation duration in seconds
    """
    SFM_BULK_STORE_TOTAL.labels(tenant=tenant, status=status).inc()
    SFM_BULK_STORE_ITEMS.labels(tenant=tenant, status="succeeded").inc(succeeded)
    SFM_BULK_STORE_ITEMS.labels(tenant=tenant, status="failed").inc(failed)
    SFM_BULK_STORE_LATENCY.labels(tenant=tenant).observe(duration_seconds)


def record_hybrid_recall(
    tenant: str,
    status: str,
    fallback: bool,
    duration_seconds: float,
) -> None:
    """Record a hybrid recall operation with metrics.

    Args:
        tenant: Tenant identifier
        status: Operation status ('success', 'error')
        fallback: Whether vector-only fallback was used
        duration_seconds: Operation duration in seconds
    """
    fallback_label = "true" if fallback else "false"
    SFM_HYBRID_RECALL_TOTAL.labels(
        tenant=tenant, status=status, fallback=fallback_label
    ).inc()
    SFM_HYBRID_RECALL_LATENCY.labels(tenant=tenant).observe(duration_seconds)


__all__ = [
    # Counters
    "SFM_REQUEST_TOTAL",
    "SFM_WM_PROMOTION_TOTAL",
    "SFM_DEGRADATION_EVENTS",
    "SFM_GRAPH_OPERATIONS",
    "SFM_BULK_STORE_TOTAL",
    "SFM_BULK_STORE_ITEMS",
    "SFM_HYBRID_RECALL_TOTAL",
    # Gauges
    "SFM_CIRCUIT_BREAKER_STATE",
    "SFM_OUTBOX_PENDING",
    # Histograms
    "SFM_REQUEST_DURATION",
    "SFM_GRAPH_LATENCY",
    "SFM_BULK_STORE_LATENCY",
    "SFM_HYBRID_RECALL_LATENCY",
    # Helper functions
    "record_sfm_request",
    "update_circuit_breaker_state",
    "update_outbox_pending",
    "record_wm_promotion",
    "record_degradation_event",
    "record_graph_operation",
    "record_bulk_store",
    "record_hybrid_recall",
]