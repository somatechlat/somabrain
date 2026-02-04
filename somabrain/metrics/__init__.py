"""Metrics module - Prometheus-based observability."""

from somabrain.metrics.core import (
    get_counter,
    get_gauge,
    get_histogram,
    get_summary,
)
from somabrain.metrics.outbox_metrics import (
    DEFAULT_TENANT_LABEL,
    report_outbox_pending,
    report_outbox_processed,
)
from somabrain.metrics.memory_metrics import (
    record_memory_snapshot,
)

__all__ = [
    "get_counter",
    "get_gauge",
    "get_histogram",
    "get_summary",
    "DEFAULT_TENANT_LABEL",
    "report_outbox_pending",
    "report_outbox_processed",
    "record_memory_snapshot",
    "advanced_math_metrics",
    "context_metrics",
    "math_metrics",
]
