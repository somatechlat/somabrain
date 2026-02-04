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

__all__ = [
    "get_counter",
    "get_gauge",
    "get_histogram",
    "get_summary",
    "DEFAULT_TENANT_LABEL",
    "report_outbox_pending",
    "report_outbox_processed",
    "record_memory_snapshot",
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
    "math_metrics",
]
