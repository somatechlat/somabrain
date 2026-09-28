"""Metrics module - Prometheus-based observability."""

from somabrain.metrics import advanced_math_metrics, context_metrics, math_metrics
from somabrain.metrics.core import (
    get_counter,
    get_gauge,
    get_histogram,
    get_summary,
    registry,
)
from somabrain.metrics.learning import (
    LEARNER_DLQ_TOTAL,
    LEARNER_EVENT_LATENCY,
    LEARNER_EVENTS_CONSUMED,
    LEARNER_EVENTS_FAILED,
    LEARNER_EVENTS_PRODUCED,
    LEARNER_LAG_SECONDS,
)
from somabrain.metrics.memory_metrics import (
    MEMORY_OUTBOX_SYNC_TOTAL,
    record_memory_snapshot,
)
from somabrain.metrics.oak import (
    MILVUS_INGEST_LAT_P95,
    MILVUS_RECONCILE_MISSING,
    MILVUS_RECONCILE_ORPHAN,
    MILVUS_SEARCH_LAT_P95,
    MILVUS_SEGMENT_LOAD,
    MILVUS_UPSERT_FAILURE_TOTAL,
    MILVUS_UPSERT_RETRY_TOTAL,
    OPTION_COUNT,
    OPTION_UTILITY_AVG,
)
from somabrain.metrics.outbox_metrics import (
    DEFAULT_TENANT_LABEL,
    report_outbox_pending,
    report_outbox_processed,
)

__all__ = [
    "DEFAULT_TENANT_LABEL",
    "LEARNER_DLQ_TOTAL",
    "LEARNER_EVENTS_CONSUMED",
    "LEARNER_EVENTS_FAILED",
    "LEARNER_EVENTS_PRODUCED",
    "LEARNER_EVENT_LATENCY",
    "LEARNER_LAG_SECONDS",
    "MEMORY_OUTBOX_SYNC_TOTAL",
    "MILVUS_INGEST_LAT_P95",
    "MILVUS_RECONCILE_MISSING",
    "MILVUS_RECONCILE_ORPHAN",
    "MILVUS_SEARCH_LAT_P95",
    "MILVUS_SEGMENT_LOAD",
    "MILVUS_UPSERT_FAILURE_TOTAL",
    "MILVUS_UPSERT_RETRY_TOTAL",
    "OPTION_COUNT",
    "OPTION_UTILITY_AVG",
    "advanced_math_metrics",
    "context_metrics",
    "get_counter",
    "get_gauge",
    "get_histogram",
    "get_summary",
    "math_metrics",
    "record_memory_snapshot",
    "registry",
    "report_outbox_pending",
    "report_outbox_processed",
]
