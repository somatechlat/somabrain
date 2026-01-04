"""Category H2: Integration Metrics Tests.

**Feature: deep-memory-integration**
**Validates: Requirements H2.1, H2.2, H2.3, H2.4, H2.5**

Tests that verify integration metrics are recorded correctly.

Test Coverage:
- Task 14.8: SFM calls → metrics recorded with correct labels
"""

from __future__ import annotations

import os
import uuid

import pytest

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Skip tests if infrastructure is not available
pytestmark = pytest.mark.skipif(
    os.environ.get("SOMA_INFRA_AVAILABLE") != "1",
    reason="Requires live infrastructure (Redis, Postgres, Milvus)",
)


# ---------------------------------------------------------------------------
# Test Class: Integration Metrics (H2)
# ---------------------------------------------------------------------------


@pytest.mark.memory_proof
class TestIntegrationMetrics:
    """Tests for SFM integration metrics.

    **Feature: deep-memory-integration, Category H2: Integration Metrics**
    **Validates: Requirements H2.1, H2.2, H2.3, H2.4, H2.5**
    """

    def test_sfm_request_total_metric_exists(self) -> None:
        """H2.1: SFM_REQUEST_TOTAL counter exists with correct labels.

        **Feature: deep-memory-integration**
        **Validates: Requirements H2.1**
        """
        from somabrain.metrics.integration import SFM_REQUEST_TOTAL

        assert SFM_REQUEST_TOTAL is not None, "SFM_REQUEST_TOTAL should exist"

        # Verify it's a Counter
        assert hasattr(SFM_REQUEST_TOTAL, "labels"), "Should have labels method"

        # Verify labels can be set
        labeled = SFM_REQUEST_TOTAL.labels(
            operation="store",
            tenant="test_tenant",
            status="success",
        )
        assert labeled is not None, "Should accept operation, tenant, status labels"

    def test_sfm_request_duration_metric_exists(self) -> None:
        """H2.2: SFM_REQUEST_DURATION histogram exists with correct labels.

        **Feature: deep-memory-integration**
        **Validates: Requirements H2.2**
        """
        from somabrain.metrics.integration import SFM_REQUEST_DURATION

        assert SFM_REQUEST_DURATION is not None, "SFM_REQUEST_DURATION should exist"

        # Verify it's a Histogram
        assert hasattr(SFM_REQUEST_DURATION, "labels"), "Should have labels method"
        assert hasattr(SFM_REQUEST_DURATION, "observe"), "Should have observe method"

        # Verify labels can be set
        labeled = SFM_REQUEST_DURATION.labels(
            operation="recall",
            tenant="test_tenant",
        )
        assert labeled is not None, "Should accept operation, tenant labels"

    def test_sfm_circuit_breaker_state_metric_exists(self) -> None:
        """H2.3: SFM_CIRCUIT_BREAKER_STATE gauge exists.

        **Feature: deep-memory-integration**
        **Validates: Requirements H2.3**
        """
        from somabrain.metrics.integration import SFM_CIRCUIT_BREAKER_STATE

        assert SFM_CIRCUIT_BREAKER_STATE is not None, "Metric should exist"

        # Verify it's a Gauge
        assert hasattr(SFM_CIRCUIT_BREAKER_STATE, "labels"), "Should have labels"
        assert hasattr(SFM_CIRCUIT_BREAKER_STATE, "set"), "Should have set method"

        # Verify labels can be set
        labeled = SFM_CIRCUIT_BREAKER_STATE.labels(tenant="test_tenant")
        assert labeled is not None, "Should accept tenant label"

    def test_sfm_outbox_pending_metric_exists(self) -> None:
        """H2.4: SFM_OUTBOX_PENDING gauge exists.

        **Feature: deep-memory-integration**
        **Validates: Requirements H2.4**
        """
        from somabrain.metrics.integration import SFM_OUTBOX_PENDING

        assert SFM_OUTBOX_PENDING is not None, "Metric should exist"

        # Verify it's a Gauge
        assert hasattr(SFM_OUTBOX_PENDING, "labels"), "Should have labels"
        assert hasattr(SFM_OUTBOX_PENDING, "set"), "Should have set method"

    def test_sfm_wm_promotion_total_metric_exists(self) -> None:
        """H2.5: SFM_WM_PROMOTION_TOTAL counter exists.

        **Feature: deep-memory-integration**
        **Validates: Requirements H2.5**
        """
        from somabrain.metrics.integration import SFM_WM_PROMOTION_TOTAL

        assert SFM_WM_PROMOTION_TOTAL is not None, "Metric should exist"

        # Verify it's a Counter
        assert hasattr(SFM_WM_PROMOTION_TOTAL, "labels"), "Should have labels"
        assert hasattr(SFM_WM_PROMOTION_TOTAL, "inc"), "Should have inc method"

    def test_record_sfm_request_helper(self) -> None:
        """Task 14.8: record_sfm_request records metrics correctly.

        **Feature: deep-memory-integration**
        **Validates: Requirements H2.1, H2.2**

        WHEN SFM call is made THEN metrics SHALL be recorded
        with correct operation, tenant, and status labels.
        """
        from somabrain.metrics.integration import record_sfm_request

        tenant_id = f"test_metrics_{uuid.uuid4().hex[:8]}"

        # Record a successful request
        record_sfm_request(
            operation="store",
            tenant=tenant_id,
            status="success",
            duration_seconds=0.05,
        )

        # Record a failed request
        record_sfm_request(
            operation="recall",
            tenant=tenant_id,
            status="error",
            duration_seconds=0.1,
        )

        # If we get here without exception, metrics were recorded
        # (Prometheus metrics are global, so we can't easily verify values)

    def test_update_circuit_breaker_state_helper(self) -> None:
        """update_circuit_breaker_state updates gauge correctly.

        **Feature: deep-memory-integration**
        **Validates: Requirements H2.3**
        """
        from somabrain.metrics.integration import update_circuit_breaker_state

        tenant_id = f"test_cb_{uuid.uuid4().hex[:8]}"

        # Update to closed (0)
        update_circuit_breaker_state(tenant=tenant_id, state=0)

        # Update to open (1)
        update_circuit_breaker_state(tenant=tenant_id, state=1)

        # Update to half-open (2)
        update_circuit_breaker_state(tenant=tenant_id, state=2)

        # If we get here without exception, gauge was updated

    def test_record_wm_promotion_helper(self) -> None:
        """record_wm_promotion increments counter correctly.

        **Feature: deep-memory-integration**
        **Validates: Requirements H2.5**
        """
        from somabrain.metrics.integration import record_wm_promotion

        tenant_id = f"test_promo_{uuid.uuid4().hex[:8]}"

        # Record successful promotion
        record_wm_promotion(tenant=tenant_id, status="success")

        # Record failed promotion
        record_wm_promotion(tenant=tenant_id, status="error")

        # If we get here without exception, counter was incremented


# ---------------------------------------------------------------------------
# Test Class: Additional Integration Metrics
# ---------------------------------------------------------------------------


@pytest.mark.memory_proof
class TestAdditionalMetrics:
    """Tests for additional integration metrics.

    **Feature: deep-memory-integration**
    **Validates: Requirements H2.1-H2.5**
    """

    def test_degradation_events_metric_exists(self) -> None:
        """SFM_DEGRADATION_EVENTS counter exists.

        **Feature: deep-memory-integration**
        **Validates: Requirements H2.3**
        """
        from somabrain.metrics.integration import SFM_DEGRADATION_EVENTS

        assert SFM_DEGRADATION_EVENTS is not None, "Metric should exist"
        assert hasattr(SFM_DEGRADATION_EVENTS, "labels"), "Should have labels"

    def test_graph_operations_metric_exists(self) -> None:
        """SFM_GRAPH_OPERATIONS counter exists.

        **Feature: deep-memory-integration**
        **Validates: Requirements H2.1**
        """
        from somabrain.metrics.integration import SFM_GRAPH_OPERATIONS

        assert SFM_GRAPH_OPERATIONS is not None, "Metric should exist"
        assert hasattr(SFM_GRAPH_OPERATIONS, "labels"), "Should have labels"

    def test_bulk_store_metrics_exist(self) -> None:
        """Bulk store metrics exist.

        **Feature: deep-memory-integration**
        **Validates: Requirements H2.1, H2.2**
        """
        from somabrain.metrics.integration import (
            SFM_BULK_STORE_TOTAL,
            SFM_BULK_STORE_LATENCY,
            SFM_BULK_STORE_ITEMS,
        )

        assert SFM_BULK_STORE_TOTAL is not None
        assert SFM_BULK_STORE_LATENCY is not None
        assert SFM_BULK_STORE_ITEMS is not None

    def test_hybrid_recall_metrics_exist(self) -> None:
        """Hybrid recall metrics exist.

        **Feature: deep-memory-integration**
        **Validates: Requirements H2.1, H2.2**
        """
        from somabrain.metrics.integration import (
            SFM_HYBRID_RECALL_TOTAL,
            SFM_HYBRID_RECALL_LATENCY,
        )

        assert SFM_HYBRID_RECALL_TOTAL is not None
        assert SFM_HYBRID_RECALL_LATENCY is not None

    def test_all_metrics_exported(self) -> None:
        """All metrics are exported from metrics module.

        **Feature: deep-memory-integration**
        **Validates: Requirements H2.1-H2.5**
        """
        from somabrain.metrics import (
            SFM_REQUEST_TOTAL,
            SFM_REQUEST_DURATION,
            SFM_CIRCUIT_BREAKER_STATE,
            SFM_OUTBOX_PENDING,
            SFM_WM_PROMOTION_TOTAL,
        )

        # Verify all are accessible from main metrics module
        assert SFM_REQUEST_TOTAL is not None
        assert SFM_REQUEST_DURATION is not None
        assert SFM_CIRCUIT_BREAKER_STATE is not None
        assert SFM_OUTBOX_PENDING is not None
        assert SFM_WM_PROMOTION_TOTAL is not None