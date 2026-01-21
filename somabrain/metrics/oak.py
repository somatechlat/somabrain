"""Oak and Milvus Metrics for SomaBrain.

This module provides metrics for Oak options (ROAMDP) and Milvus
vector database operations.

Metrics:
- OPTION_UTILITY_AVG: Average utility of created Oak options per tenant
- OPTION_COUNT: Total number of Oak options stored per tenant
- MILVUS_SEARCH_LAT_P95: p95 search latency to Milvus
- MILVUS_INGEST_LAT_P95: p95 ingest latency to Milvus
- MILVUS_SEGMENT_LOAD: Number of Milvus query segments loaded
- MILVUS_UPSERT_RETRY_TOTAL: Retry attempts during Milvus option upserts
- MILVUS_UPSERT_FAILURE_TOTAL: Failed Milvus option upserts after retries
- MILVUS_RECONCILE_MISSING: Missing vectors inserted during reconciliation
- MILVUS_RECONCILE_ORPHAN: Orphan vectors removed during reconciliation
"""

from __future__ import annotations

from somabrain.metrics.core import get_counter, get_gauge

# ---------------------------------------------------------------------------
# Oak-specific Observability (ROAMDP)
# ---------------------------------------------------------------------------

OPTION_UTILITY_AVG = get_gauge(
    "somabrain_option_utility_avg",
    "Average utility of created Oak options per tenant",
    ["tenant_id"],
)

OPTION_COUNT = get_gauge(
    "somabrain_option_count",
    "Total number of Oak options stored per tenant",
    ["tenant_id"],
)

# ---------------------------------------------------------------------------
# Milvus Telemetry
# ---------------------------------------------------------------------------

MILVUS_SEARCH_LAT_P95 = get_gauge(
    "somabrain_milvus_search_latency_p95_seconds",
    "p95 search latency to Milvus",
    ["tenant_id"],
)

MILVUS_INGEST_LAT_P95 = get_gauge(
    "somabrain_milvus_ingest_latency_p95_seconds",
    "p95 ingest latency to Milvus",
    ["tenant_id"],
)

MILVUS_SEGMENT_LOAD = get_gauge(
    "somabrain_milvus_segment_load",
    "Number of Milvus query segments currently loaded for a collection",
    ["collection"],
)

MILVUS_UPSERT_RETRY_TOTAL = get_counter(
    "somabrain_milvus_upsert_retry_total",
    "Retry attempts while persisting Oak options to Milvus",
    ["tenant_id"],
)

MILVUS_UPSERT_FAILURE_TOTAL = get_counter(
    "somabrain_milvus_upsert_failure_total",
    "Number of Milvus option upserts that failed after all retries",
    ["tenant_id"],
)

# ---------------------------------------------------------------------------
# Milvus <-> PostgreSQL Reconciliation Metrics
# ---------------------------------------------------------------------------

MILVUS_RECONCILE_MISSING = get_counter(
    "somabrain_milvus_reconcile_missing_total",
    "Number of missing option vectors inserted into Milvus during reconciliation",
    ["tenant_id"],
)

MILVUS_RECONCILE_ORPHAN = get_counter(
    "somabrain_milvus_reconcile_orphan_total",
    "Number of orphan option vectors removed from Milvus during reconciliation",
    ["tenant_id"],
)

__all__ = [
    "OPTION_UTILITY_AVG",
    "OPTION_COUNT",
    "MILVUS_SEARCH_LAT_P95",
    "MILVUS_INGEST_LAT_P95",
    "MILVUS_SEGMENT_LOAD",
    "MILVUS_UPSERT_RETRY_TOTAL",
    "MILVUS_UPSERT_FAILURE_TOTAL",
    "MILVUS_RECONCILE_MISSING",
    "MILVUS_RECONCILE_ORPHAN",
]
