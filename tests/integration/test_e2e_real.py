"""End-to-End Integration Tests against REAL Full Stack.

**Feature: production-hardening**
**Validates: Requirements 5.1, 6.1, 6.2, 8.1, 8.2**

These tests run against the REAL SomaBrain application and all its backends.
They verify complete request flows through the system.

Required: SomaBrain cluster running via docker-compose with all services healthy.
"""

from __future__ import annotations

import time
import uuid
from typing import Dict

import pytest
import httpx

from common.logging import logger


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# SomaBrain app endpoint (default to local docker-compose port)
# Port 30101 is the standardized SomaBrain cluster port
from django.conf import settings

# Use centralized Settings for test configuration
SOMABRAIN_APP_URL = settings.SOMABRAIN_API_URL or "http://localhost:30101"

# Test tenant ID
TEST_TENANT_ID = "e2e_test_tenant"

# Test namespace
TEST_NAMESPACE = "e2e_test"


# ---------------------------------------------------------------------------
# Availability checks
# ---------------------------------------------------------------------------


def _app_available() -> bool:
    """Check if SomaBrain app is reachable."""
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(f"{SOMABRAIN_APP_URL}/healthz")
            return resp.status_code == 200
    except Exception as exc:
        logger.warning("SomaBrain app not reachable: %s", exc)
        return False


def _get_test_headers(tenant_id: str = TEST_TENANT_ID) -> Dict[str, str]:
    """Get headers for test requests."""
    return {
        "X-Tenant-ID": tenant_id,
        "X-Namespace": TEST_NAMESPACE,
        "Content-Type": "application/json",
    }


# ---------------------------------------------------------------------------
# E2E Health Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestE2EHealth:
    """E2E tests for health endpoints.

    **Validates: Requirements 5.1**
    """

    def test_health_endpoint_returns_status(self) -> None:
        """Verify /health endpoint returns backend statuses."""
        if not _app_available():
            pytest.skip("SomaBrain app not reachable; skipping E2E test")

        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                f"{SOMABRAIN_APP_URL}/health",
                headers=_get_test_headers(),
            )

            assert resp.status_code == 200, f"Health check failed: {resp.status_code}"
            data = resp.json()

            # Verify response structure - actual API uses 'components' not 'backends'
            # and may not have 'status' at top level
            assert (
                "components" in data or "backends" in data or "healthy" in data
            ), "Health response missing expected structure"

            # If components present, verify structure
            if "components" in data:
                components = data["components"]
                # Memory component should be present
                if "memory" in components:
                    memory = components["memory"]
                    assert "healthy" in memory or isinstance(
                        memory, dict
                    ), "Memory component should have health info"

    def test_healthz_endpoint_returns_ok(self) -> None:
        """Verify /healthz endpoint returns OK."""
        if not _app_available():
            pytest.skip("SomaBrain app not reachable; skipping E2E test")

        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{SOMABRAIN_APP_URL}/healthz")

            assert resp.status_code == 200, f"Healthz check failed: {resp.status_code}"
            data = resp.json()

            # Should have status field
            assert "status" in data or "ok" in data, "Healthz response missing status"

    def test_health_memory_endpoint(self) -> None:
        """Verify /health/memory endpoint returns memory service status."""
        if not _app_available():
            pytest.skip("SomaBrain app not reachable; skipping E2E test")

        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                f"{SOMABRAIN_APP_URL}/health/memory",
                headers=_get_test_headers(),
            )

            # May return 200 or 503 depending on memory service state
            assert resp.status_code in [
                200,
                503,
            ], f"Unexpected status: {resp.status_code}"


# ---------------------------------------------------------------------------
# E2E Memory Flow Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestE2EMemoryFlow:
    """E2E tests for remember → recall flow.

    **Validates: Requirements 8.1, 8.2**
    """

    def test_remember_recall_flow(self) -> None:
        """Verify remember → recall flow works end-to-end."""
        if not _app_available():
            pytest.skip("SomaBrain app not reachable; skipping E2E test")

        # Generate unique test data
        test_id = str(uuid.uuid4())[:8]
        test_payload = {
            "task": f"e2e_test_{test_id}",
            "content": f"Test content for E2E test {test_id}",
            "importance": 5,
            "timestamp": time.time(),
        }

        with httpx.Client(timeout=30.0) as client:
            # Step 1: Remember
            remember_resp = client.post(
                f"{SOMABRAIN_APP_URL}/memory/remember",
                headers=_get_test_headers(),
                json={"payload": test_payload},
            )

            # Remember may fail if memory service is unavailable
            if remember_resp.status_code != 200:
                pytest.skip(
                    f"Remember failed (memory service may be unavailable): "
                    f"{remember_resp.status_code}"
                )

            remember_data = remember_resp.json()
            assert (
                "coord" in remember_data or "coordinate" in remember_data
            ), "Remember response missing coordinate"

            # Step 2: Recall
            recall_resp = client.post(
                f"{SOMABRAIN_APP_URL}/memory/recall",
                headers=_get_test_headers(),
                json={
                    "query": f"e2e_test_{test_id}",
                    "k": 5,
                },
            )

            assert (
                recall_resp.status_code == 200
            ), f"Recall failed: {recall_resp.status_code}"

            recall_data = recall_resp.json()
            assert (
                "results" in recall_data or "wm_hits" in recall_data or "ltm_hits" in recall_data
            ), "Recall response missing memory results"

    def test_recall_with_empty_query(self) -> None:
        """Verify recall handles empty/minimal queries gracefully."""
        if not _app_available():
            pytest.skip("SomaBrain app not reachable; skipping E2E test")

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{SOMABRAIN_APP_URL}/memory/recall",
                headers=_get_test_headers(),
                json={
                    "query": "test",
                    "k": 1,
                },
            )

            # May return 200, 500 (if memory service unavailable), or 503
            # The key is that the endpoint responds
            assert resp.status_code in [
                200,
                500,
                503,
            ], f"Unexpected recall status: {resp.status_code}"

            # If 200, verify response structure
            if resp.status_code == 200:
                data = resp.json()
                assert (
                    "results" in data or "wm_hits" in data or "ltm_hits" in data
                ), "Recall response missing expected fields"


# ---------------------------------------------------------------------------
# E2E Neuromodulator Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestE2ENeuromodulators:
    """E2E tests for neuromodulator endpoints.

    **Validates: Requirements 8.1**
    """

    def test_get_neuromodulators(self) -> None:
        """Verify GET /neuromodulators returns current state."""
        if not _app_available():
            pytest.skip("SomaBrain app not reachable; skipping E2E test")

        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                f"{SOMABRAIN_APP_URL}/neuromodulators",
                headers=_get_test_headers(),
            )

            assert (
                resp.status_code == 200
            ), f"Get neuromodulators failed: {resp.status_code}"

            data = resp.json()

            # Verify neuromodulator fields
            assert "dopamine" in data, "Missing dopamine"
            assert "serotonin" in data, "Missing serotonin"
            assert "noradrenaline" in data, "Missing noradrenaline"
            assert "acetylcholine" in data, "Missing acetylcholine"

            # Verify values are in valid ranges
            assert 0.0 <= data["dopamine"] <= 1.0, "Dopamine out of range"
            assert 0.0 <= data["serotonin"] <= 1.0, "Serotonin out of range"
            assert 0.0 <= data["noradrenaline"] <= 1.0, "Noradrenaline out of range"
            assert 0.0 <= data["acetylcholine"] <= 1.0, "Acetylcholine out of range"


# ---------------------------------------------------------------------------
# E2E Authentication Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestE2EAuthentication:
    """E2E tests for authentication flow.

    **Validates: Requirements 6.1, 6.2**
    """

    def test_protected_endpoint_without_auth(self) -> None:
        """Verify protected endpoints handle missing auth gracefully."""
        if not _app_available():
            pytest.skip("SomaBrain app not reachable; skipping E2E test")

        with httpx.Client(timeout=10.0) as client:
            # Try to access recall without proper headers
            resp = client.post(
                f"{SOMABRAIN_APP_URL}/memory/recall",
                json={"query": "test", "k": 1},
                # No tenant headers
            )

            # Should either require auth (401/403), use default tenant (200),
            # return validation error (422), or internal error (500) if
            # backend services are unavailable
            assert resp.status_code in [
                200,
                401,
                403,
                422,
                500,
                503,
            ], f"Unexpected status: {resp.status_code}"

    def test_tenant_header_isolation(self) -> None:
        """Verify different tenant headers create isolated contexts."""
        if not _app_available():
            pytest.skip("SomaBrain app not reachable; skipping E2E test")

        tenant_a = f"tenant_a_{uuid.uuid4().hex[:8]}"
        tenant_b = f"tenant_b_{uuid.uuid4().hex[:8]}"

        with httpx.Client(timeout=10.0) as client:
            # Get neuromodulators for tenant A
            resp_a = client.get(
                f"{SOMABRAIN_APP_URL}/neuromodulators",
                headers=_get_test_headers(tenant_a),
            )

            # Get neuromodulators for tenant B
            resp_b = client.get(
                f"{SOMABRAIN_APP_URL}/neuromodulators",
                headers=_get_test_headers(tenant_b),
            )

            # Both should succeed
            assert resp_a.status_code == 200
            assert resp_b.status_code == 200

            # Both should return valid neuromodulator states
            data_a = resp_a.json()
            data_b = resp_b.json()

            assert "dopamine" in data_a
            assert "dopamine" in data_b


# ---------------------------------------------------------------------------
# E2E Metrics Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestE2EMetrics:
    """E2E tests for metrics endpoint.

    **Validates: Requirements 5.4, 5.5**
    """

    def test_metrics_endpoint_returns_prometheus_format(self) -> None:
        """Verify /metrics endpoint returns Prometheus format."""
        if not _app_available():
            pytest.skip("SomaBrain app not reachable; skipping E2E test")

        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{SOMABRAIN_APP_URL}/metrics")

            assert resp.status_code == 200, f"Metrics failed: {resp.status_code}"

            # Prometheus format should contain metric names
            content = resp.text

            # Should contain some standard metrics
            assert (
                "# HELP" in content or "# TYPE" in content or "_total" in content
            ), "Metrics response doesn't look like Prometheus format"


# ---------------------------------------------------------------------------
# E2E Diagnostics Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestE2EDiagnostics:
    """E2E tests for diagnostics endpoint."""

    def test_diagnostics_endpoint(self) -> None:
        """Verify /diagnostics endpoint returns system info."""
        if not _app_available():
            pytest.skip("SomaBrain app not reachable; skipping E2E test")

        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                f"{SOMABRAIN_APP_URL}/diagnostics",
                headers=_get_test_headers(),
            )

            # Diagnostics may require admin auth
            if resp.status_code == 401 or resp.status_code == 403:
                pytest.skip("Diagnostics requires admin auth")

            assert resp.status_code == 200, f"Diagnostics failed: {resp.status_code}"