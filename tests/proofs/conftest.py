"""Shared fixtures for SomaBrain Full Capacity Real-World Testing.

This module provides session-scoped fixtures for:
- Docker infrastructure health verification
- Tenant isolation testing
- API client management
- Backend availability checks

All tests run against REAL Docker infrastructure - NO mocks.
"""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass
from typing import Dict, Generator, List, Optional

import httpx
import pytest

try:
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=".env", override=False)
except Exception:
    pass

from django.conf import settings


# ---------------------------------------------------------------------------
# Configuration from centralized Settings
# ---------------------------------------------------------------------------

SOMABRAIN_APP_URL = settings.SOMABRAIN_API_URL or "http://localhost:30101"
MEMORY_URL = settings.SOMABRAIN_MEMORY_HTTP_ENDPOINT or "http://localhost:9595"
MEMORY_TOKEN = settings.SOMABRAIN_MEMORY_HTTP_TOKEN

# Docker service ports (from docker-compose.yml)
REDIS_PORT = int(os.getenv("REDIS_HOST_PORT", "30100"))
KAFKA_PORT = int(os.getenv("KAFKA_BROKER_HOST_PORT", "30102"))
POSTGRES_PORT = int(os.getenv("POSTGRES_HOST_PORT", "30106"))
MILVUS_PORT = int(os.getenv("MILVUS_GRPC_HOST_PORT", "30119"))
OPA_PORT = int(os.getenv("OPA_HOST_PORT", "30104"))
PROMETHEUS_PORT = int(os.getenv("PROMETHEUS_HOST_PORT", "30105"))
JAEGER_PORT = int(os.getenv("JAEGER_HOST_PORT", "30111"))


# ---------------------------------------------------------------------------
# Data Classes for Test Results
# ---------------------------------------------------------------------------


@dataclass
class BackendHealth:
    """Health status of a backend service."""

    name: str
    healthy: bool
    latency_ms: float
    error: Optional[str] = None


@dataclass
class InfrastructureHealth:
    """Overall infrastructure health status."""

    all_healthy: bool
    backends: Dict[str, BackendHealth]
    timestamp: float


# ---------------------------------------------------------------------------
# Backend Availability Checks
# ---------------------------------------------------------------------------


def _check_redis_health() -> BackendHealth:
    """Check Redis availability via TCP connection."""
    import socket

    start = time.time()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        result = sock.connect_ex(("localhost", REDIS_PORT))
        sock.close()
        latency = (time.time() - start) * 1000
        if result == 0:
            return BackendHealth("redis", True, latency)
        return BackendHealth(
            "redis", False, latency, f"Connection refused on port {REDIS_PORT}"
        )
    except Exception as e:
        return BackendHealth("redis", False, (time.time() - start) * 1000, str(e))


def _check_kafka_health() -> BackendHealth:
    """Check Kafka availability via TCP connection."""
    import socket

    start = time.time()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        result = sock.connect_ex(("localhost", KAFKA_PORT))
        sock.close()
        latency = (time.time() - start) * 1000
        if result == 0:
            return BackendHealth("kafka", True, latency)
        return BackendHealth(
            "kafka", False, latency, f"Connection refused on port {KAFKA_PORT}"
        )
    except Exception as e:
        return BackendHealth("kafka", False, (time.time() - start) * 1000, str(e))


def _check_postgres_health() -> BackendHealth:
    """Check Postgres availability via TCP connection."""
    import socket

    start = time.time()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        result = sock.connect_ex(("localhost", POSTGRES_PORT))
        sock.close()
        latency = (time.time() - start) * 1000
        if result == 0:
            return BackendHealth("postgres", True, latency)
        return BackendHealth(
            "postgres", False, latency, f"Connection refused on port {POSTGRES_PORT}"
        )
    except Exception as e:
        return BackendHealth("postgres", False, (time.time() - start) * 1000, str(e))


def _check_milvus_health() -> BackendHealth:
    """Check Milvus availability via HTTP health endpoint."""
    start = time.time()
    try:
        # Milvus HTTP health endpoint is on port 9091 (mapped to 30120)
        milvus_http_port = int(os.getenv("MILVUS_HTTP_HOST_PORT", "30120"))
        r = httpx.get(f"http://localhost:{milvus_http_port}/healthz", timeout=5.0)
        latency = (time.time() - start) * 1000
        if r.status_code == 200:
            return BackendHealth("milvus", True, latency)
        return BackendHealth("milvus", False, latency, f"HTTP {r.status_code}")
    except Exception as e:
        return BackendHealth("milvus", False, (time.time() - start) * 1000, str(e))


def _check_opa_health() -> BackendHealth:
    """Check OPA availability via health endpoint."""
    start = time.time()
    try:
        r = httpx.get(f"http://localhost:{OPA_PORT}/health", timeout=2.0)
        latency = (time.time() - start) * 1000
        if r.status_code == 200:
            return BackendHealth("opa", True, latency)
        return BackendHealth("opa", False, latency, f"HTTP {r.status_code}")
    except Exception as e:
        return BackendHealth("opa", False, (time.time() - start) * 1000, str(e))


def _check_app_health() -> BackendHealth:
    """Check SomaBrain app availability via health endpoint."""
    start = time.time()
    try:
        r = httpx.get(f"{SOMABRAIN_APP_URL}/health", timeout=5.0)
        latency = (time.time() - start) * 1000
        if r.status_code == 200:
            return BackendHealth("somabrain_app", True, latency)
        return BackendHealth("somabrain_app", False, latency, f"HTTP {r.status_code}")
    except Exception as e:
        return BackendHealth(
            "somabrain_app", False, (time.time() - start) * 1000, str(e)
        )


# ---------------------------------------------------------------------------
# Session-Scoped Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def infrastructure_health() -> InfrastructureHealth:
    """Check health of all Docker infrastructure services.

    Returns InfrastructureHealth with status of all backends.
    Tests can use this to skip if required backends are unavailable.
    """
    backends = {
        "redis": _check_redis_health(),
        "kafka": _check_kafka_health(),
        "postgres": _check_postgres_health(),
        "milvus": _check_milvus_health(),
        "opa": _check_opa_health(),
        "somabrain_app": _check_app_health(),
    }
    all_healthy = all(b.healthy for b in backends.values())
    return InfrastructureHealth(
        all_healthy=all_healthy,
        backends=backends,
        timestamp=time.time(),
    )


@pytest.fixture(scope="session")
def require_all_backends(infrastructure_health: InfrastructureHealth) -> None:
    """Skip test if any backend is unhealthy."""
    if not infrastructure_health.all_healthy:
        unhealthy = [
            f"{name}: {b.error}"
            for name, b in infrastructure_health.backends.items()
            if not b.healthy
        ]
        pytest.skip(f"Required backends unavailable: {', '.join(unhealthy)}")


@pytest.fixture(scope="session")
def require_redis(infrastructure_health: InfrastructureHealth) -> None:
    """Skip test if Redis is unavailable."""
    redis = infrastructure_health.backends.get("redis")
    if not redis or not redis.healthy:
        pytest.skip(f"Redis unavailable: {redis.error if redis else 'not checked'}")


@pytest.fixture(scope="session")
def require_milvus(infrastructure_health: InfrastructureHealth) -> None:
    """Skip test if Milvus is unavailable."""
    milvus = infrastructure_health.backends.get("milvus")
    if not milvus or not milvus.healthy:
        pytest.skip(f"Milvus unavailable: {milvus.error if milvus else 'not checked'}")


@pytest.fixture(scope="session")
def require_app(infrastructure_health: InfrastructureHealth) -> None:
    """Skip test if SomaBrain app is unavailable."""
    app = infrastructure_health.backends.get("somabrain_app")
    if not app or not app.healthy:
        pytest.skip(f"SomaBrain app unavailable: {app.error if app else 'not checked'}")


@pytest.fixture(scope="session")
def api_client(require_app: None) -> Generator[httpx.Client, None, None]:
    """HTTP client for SomaBrain API.

    Session-scoped, automatically skips if app is unavailable.
    """
    client = httpx.Client(base_url=SOMABRAIN_APP_URL, timeout=30.0)
    yield client
    client.close()


# ---------------------------------------------------------------------------
# Tenant Isolation Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def unique_tenant_id() -> str:
    """Generate a unique tenant ID for isolation testing."""
    return f"test_tenant_{uuid.uuid4().hex[:12]}"


@pytest.fixture
def tenant_pair() -> tuple[str, str]:
    """Generate a pair of unique tenant IDs for cross-tenant testing."""
    return (
        f"tenant_a_{uuid.uuid4().hex[:8]}",
        f"tenant_b_{uuid.uuid4().hex[:8]}",
    )


@pytest.fixture
def multi_tenant_ids() -> List[str]:
    """Generate 100 unique tenant IDs for concurrent isolation testing."""
    return [f"tenant_{i:03d}_{uuid.uuid4().hex[:6]}" for i in range(100)]


def get_tenant_headers(tenant_id: str, namespace: str = "test") -> Dict[str, str]:
    """Get HTTP headers for a specific tenant."""
    return {
        "X-Tenant-ID": tenant_id,
        "X-Namespace": namespace,
        "Content-Type": "application/json",
    }


# ---------------------------------------------------------------------------
# Pytest Markers
# ---------------------------------------------------------------------------


def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers for test categorization."""
    config.addinivalue_line(
        "markers", "math_proof: Category A - Mathematical Core Proofs"
    )
    config.addinivalue_line(
        "markers", "memory_proof: Category B - Memory System Proofs"
    )
    config.addinivalue_line(
        "markers", "cognitive_proof: Category C - Cognitive Function Proofs"
    )
    config.addinivalue_line(
        "markers", "isolation_proof: Category D - Multi-Tenant Isolation Proofs"
    )
    config.addinivalue_line(
        "markers", "infrastructure: Category E - Infrastructure Requirements"
    )
    config.addinivalue_line(
        "markers", "circuit_breaker: Category F - Circuit Breaker Proofs"
    )
    config.addinivalue_line("markers", "performance: Category G - Performance Proofs")
    config.addinivalue_line(
        "markers", "requires_docker: Requires Docker infrastructure"
    )
    config.addinivalue_line("markers", "slow: Long-running tests")