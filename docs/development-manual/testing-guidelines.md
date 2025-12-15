# Testing Guidelines

**Purpose**: Comprehensive testing standards and practices for SomaBrain development, covering unit testing, integration testing, and quality assurance.

**Audience**: Software developers, QA engineers, and DevOps teams working on SomaBrain testing infrastructure.

**Prerequisites**: Understanding of [Coding Standards](coding-standards.md) and [Local Setup](local-setup.md).

---

## VIBE CODING RULES COMPLIANCE

**CRITICAL**: All tests in SomaBrain MUST use REAL services. The following are STRICTLY FORBIDDEN:

- Mock objects (unittest.mock.Mock, AsyncMock, MagicMock)
- Fake implementations
- Stub services
- Placeholder data
- In-memory substitutes for real databases

Tests that cannot run against real services should be skipped with a clear message indicating the required service.

---

## Testing Philosophy

### Testing Principles

**Real Services Only**: All tests run against actual infrastructure (Postgres, Redis, Kafka, Memory Service)
**Comprehensive Coverage**: Aim for high test coverage while focusing on critical paths
**Fast Feedback**: Tests should run quickly to enable rapid development iteration
**Deterministic**: Tests must produce consistent results across environments
**Maintainable**: Test code should follow the same quality standards as production code

### Testing Pyramid

```
    E2E Tests (Few)
    ================
   Integration Tests (Some)
   ========================
  Unit Tests (Many)
  ====================
```

**Unit Tests (70%)**: Fast tests for pure functions and deterministic logic (no I/O)
**Integration Tests (20%)**: Test interactions between components using real services
**End-to-End Tests (10%)**: Full system tests against the complete stack

---

## Unit Testing Standards

### Python Unit Testing with pytest

Unit tests should focus on pure functions and deterministic logic that does not require external services.

```python
# tests/conftest.py - Shared test configuration
import pytest
import asyncio
import os
from datetime import datetime
from typing import Generator, AsyncGenerator
import numpy as np

from common.config.settings import settings

# Pytest configuration
def pytest_configure(config):
    """Configure pytest settings."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "e2e: mark test as an end-to-end test")
    config.addinivalue_line("markers", "slow: mark test as slow running")

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def require_postgres():
    """Skip test if Postgres is not available."""
    dsn = settings.postgres_dsn
    if not dsn:
        pytest.skip("Postgres DSN (SOMABRAIN_POSTGRES_DSN) required")
    return dsn

@pytest.fixture
def require_redis():
    """Skip test if Redis is not available."""
    url = settings.redis_url
    if not url:
        pytest.skip("Redis URL (SOMABRAIN_REDIS_URL) required")
    return url

@pytest.fixture
def require_memory_service():
    """Skip test if Memory service is not available."""
    import httpx
    endpoint = settings.memory_http_endpoint
    if not endpoint:
        pytest.skip("Memory service endpoint required")
    try:
        resp = httpx.get(f"{endpoint}/health", timeout=2.0)
        if resp.status_code != 200:
            pytest.skip(f"Memory service not healthy at {endpoint}")
    except Exception as e:
        pytest.skip(f"Memory service not reachable at {endpoint}: {e}")
    return endpoint


# Example unit tests for PURE functions only
# tests/unit/test_numerics.py
import pytest
import numpy as np
from somabrain.numerics import normalize_array, compute_tiny_floor

@pytest.mark.unit
class TestNumerics:
    """Unit tests for pure numeric functions."""

    def test_normalize_array_unit_vector(self):
        """Test normalization produces unit vectors."""
        vec = np.array([3.0, 4.0], dtype=np.float32)
        result = normalize_array(vec)
        norm = np.linalg.norm(result)
        assert abs(norm - 1.0) < 1e-6

    def test_normalize_array_zero_vector(self):
        """Test normalization handles zero vectors."""
        vec = np.zeros(10, dtype=np.float32)
        result = normalize_array(vec)
        # Should return zero vector or baseline, not raise
        assert result.shape == vec.shape

    def test_compute_tiny_floor_positive(self):
        """Test tiny floor is always positive."""
        for dim in [64, 256, 1024, 4096]:
            floor = compute_tiny_floor(dim, np.float32)
            assert floor > 0

    def test_compute_tiny_floor_scales_with_dimension(self):
        """Test tiny floor scales appropriately with dimension."""
        floor_small = compute_tiny_floor(64, np.float32)
        floor_large = compute_tiny_floor(4096, np.float32)
        # Larger dimensions should have larger floors (sqrt strategy)
        assert floor_large > floor_small
```

---

## Integration Testing

### Requirements

All integration tests MUST:
1. Use real Postgres database
2. Use real Redis instance
3. Use real Memory HTTP service
4. Use real Kafka cluster (when testing event flows)

### Database Integration Tests

```python
# tests/integration/test_database_integration.py
import pytest
import asyncio
import os
import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from common.config.settings import settings

@pytest.fixture(scope="session")
async def test_database(require_postgres):
    """Connect to real test database."""
    database_url = require_postgres

    engine = create_engine(database_url)
    SessionLocal = sessionmaker(bind=engine)

    yield {
        "url": database_url,
        "engine": engine,
        "session_factory": SessionLocal
    }

    # Cleanup test data after session
    engine.dispose()

@pytest.mark.integration
class TestDatabaseIntegration:
    """Integration tests for database operations using REAL Postgres."""

    @pytest.mark.asyncio
    async def test_store_and_retrieve_memory(self, test_database):
        """Test complete memory storage and retrieval workflow."""
        from somabrain.database.connection import DatabaseManager

        async with DatabaseManager(test_database["url"]) as db_manager:
            # Store memory
            memory_id = await db_manager.store_memory(
                content="Integration test memory content",
                metadata={"category": "integration_test"},
                vector_encoding=np.random.rand(384).astype(np.float32),
                tenant_id="test_tenant"
            )

            assert memory_id is not None

            # Retrieve memory
            retrieved = await db_manager.get_memory(memory_id, "test_tenant")
            assert retrieved is not None
            assert retrieved.content == "Integration test memory content"

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, test_database):
        """Test that tenant isolation works correctly."""
        from somabrain.database.connection import DatabaseManager

        async with DatabaseManager(test_database["url"]) as db_manager:
            # Store memory for tenant A
            memory_id_a = await db_manager.store_memory(
                content="Tenant A memory",
                metadata={"tenant": "A"},
                vector_encoding=np.random.rand(384).astype(np.float32),
                tenant_id="tenant_a"
            )

            # Store memory for tenant B
            memory_id_b = await db_manager.store_memory(
                content="Tenant B memory",
                metadata={"tenant": "B"},
                vector_encoding=np.random.rand(384).astype(np.float32),
                tenant_id="tenant_b"
            )

            # Verify tenant A cannot access tenant B's memory
            cross_access = await db_manager.get_memory(memory_id_b, "tenant_a")
            assert cross_access is None

            # Verify each tenant can access their own memory
            memory_a = await db_manager.get_memory(memory_id_a, "tenant_a")
            memory_b = await db_manager.get_memory(memory_id_b, "tenant_b")
            assert memory_a is not None
            assert memory_b is not None
```

### API Integration Tests

```python
# tests/integration/test_api_integration.py
import pytest
import httpx
import os

from common.config.settings import settings

@pytest.fixture
def api_client(require_memory_service):
    """Create HTTP client for real API."""
    base_url = settings.default_base_url or "http://localhost:9696"
    with httpx.Client(base_url=base_url, timeout=30.0) as client:
        yield client

@pytest.mark.integration
class TestAPIIntegration:
    """Integration tests for API endpoints using REAL services."""

    def test_health_endpoint(self, api_client):
        """Test health check endpoint."""
        response = api_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        # Verify real service health
        assert "memory_ok" in data or "healthy" in data

    def test_remember_and_recall_workflow(self, api_client):
        """Test complete remember and recall workflow against REAL services."""
        import uuid

        # Generate unique content to avoid test interference
        unique_content = f"Integration test content {uuid.uuid4()}"

        # Store a memory
        remember_response = api_client.post(
            "/memory/remember",
            json={
                "payload": {
                    "task": unique_content,
                    "content": "FastAPI is a modern web framework for Python"
                }
            },
            headers={"X-Tenant-ID": "integration_test"}
        )

        assert remember_response.status_code == 200
        memory_data = remember_response.json()
        assert "coordinate" in memory_data or "coord" in memory_data

        # Recall memories
        recall_response = api_client.post(
            "/memory/recall",
            json={
                "query": unique_content,
                "top_k": 5
            },
            headers={"X-Tenant-ID": "integration_test"}
        )

        assert recall_response.status_code == 200
        recall_data = recall_response.json()
        assert "results" in recall_data
```

---

## End-to-End Testing

### Live Stack Integration

The repository includes E2E tests that exercise the live API surface and attached services.

**Requirements**:
- Docker Compose stack running (Kafka, Postgres, Redis, OPA, Prometheus)
- Real external Memory HTTP service on port 9595
- All services healthy

### Running E2E Tests

```bash
# 1. Start the full stack
scripts/dev_up.sh

# 2. Verify all services are healthy
curl -f http://localhost:9696/health
curl -f http://localhost:9595/health  # Memory service

# 3. Run E2E tests
pytest -q tests/e2e

# 4. Run integration tests
pytest -q tests/integration
```

### What E2E Tests Cover

- `test_e2e_memory_http.py`: Exercises POST /remember and POST /recall against REAL memory service
- `test_embedded_services_http.py`: Probes /reward/health and /learner/health
- `test_reward_post_embedded.py`: Posts rewards via real Kafka
- `test_observability_http.py`: Verifies Prometheus, exporters, and OPA

---

## Test Data Management

### Guidelines

1. **Use unique identifiers**: Generate UUIDs for test data to avoid conflicts
2. **Clean up after tests**: Remove test data in teardown fixtures
3. **Isolate by tenant**: Use dedicated test tenant IDs
4. **Mark test data clearly**: Include "test" or "integration" in metadata

```python
import uuid

@pytest.fixture
def test_tenant_id():
    """Generate unique tenant ID for test isolation."""
    return f"test_tenant_{uuid.uuid4().hex[:8]}"

@pytest.fixture
def cleanup_test_data(test_tenant_id, api_client):
    """Cleanup fixture to remove test data after tests."""
    created_ids = []
    yield created_ids
    # Cleanup logic here if needed
```

---

## CI/CD Integration

### GitHub Actions Configuration

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: soma
          POSTGRES_PASSWORD: soma_pass
          POSTGRES_DB: somabrain_test
        ports:
          - 5432:5432
      redis:
        image: redis:7
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v4

      - name: Enforce no stubs (fail fast)
        run: bash scripts/ci/forbid_stubs.sh

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: pip install -e ".[dev]"

      - name: Run unit tests
        run: pytest tests/unit -v --tb=short

      - name: Run integration tests
        env:
          SOMABRAIN_POSTGRES_DSN: postgresql://soma:soma_pass@localhost:5432/somabrain_test
          SOMABRAIN_REDIS_URL: redis://localhost:6379/0
        run: pytest tests/integration -v --tb=short
```

---

## Forbidden Patterns

The following patterns are STRICTLY FORBIDDEN in SomaBrain tests:

```python
# FORBIDDEN - Do not use mocks
from unittest.mock import Mock, AsyncMock, MagicMock, patch
mock_service = Mock()  # VIOLATION
async_mock = AsyncMock()  # VIOLATION

# FORBIDDEN - Do not use fake implementations
class FakeMemoryService:  # VIOLATION
    pass

# FORBIDDEN - Do not use in-memory databases
database_url = "sqlite:///:memory:"  # VIOLATION

# FORBIDDEN - Do not use placeholder data
placeholder_response = {"status": "ok"}  # VIOLATION if used to bypass real service
```

### Correct Patterns

```python
# CORRECT - Skip if service unavailable
@pytest.fixture
def require_service():
    if not service_available():
        pytest.skip("Real service required")
    return real_service_client()

# CORRECT - Use real services
def test_with_real_database(require_postgres):
    # Test runs against real Postgres
    pass

# CORRECT - Generate real test data
def test_store_memory(api_client):
    real_content = f"Test content {uuid.uuid4()}"
    response = api_client.post("/memory/remember", json={"content": real_content})
    assert response.status_code == 200
```

---

## Summary

SomaBrain testing follows strict VIBE Coding Rules:

1. **NO MOCKS** - All tests use real services
2. **NO PLACEHOLDERS** - All data is real or clearly marked test data
3. **NO STUBS** - Skip tests if services unavailable, don't fake them
4. **REAL INFRASTRUCTURE** - Postgres, Redis, Kafka, Memory Service must be running

---

## Recall Testing Workbench (integration)

**Purpose**: Prove recall correctness, degradation flag presence, tenant isolation, and latency SLOs against the live memory service.

**Env vars (required)**  
- `SOMABRAIN_MEMORY_HTTP_ENDPOINT` (default fallback: `http://localhost:9595`)  
- `SOMABRAIN_MEMORY_HTTP_TOKEN` (dev token lives in `.env`)  
- `SOMABRAIN_API_URL` (default fallback: `http://localhost:9696`)  
- `SOMABRAIN_POSTGRES_DSN` for any DB-backed flows.

**How to run (local stack up via docker compose)**  
```bash
source .venv/bin/activate
pytest tests/integration/test_recall_quality.py
```

**What it checks**
- Quality: precision/recall/nDCG on a small labeled corpus (`test_recall_quality_basic`).
- Isolation: tenant A results never include tenant B payloads.
- Degraded flag: `/recall` response includes `degraded` field (schema truth).

**Latency/SLO (optional)**
- Use `benchmarks/recall_latency_bench.py` with live stack to verify p95 targets (remember <300 ms, recall <400 ms). Example:
```bash
SOMABRAIN_API_URL=http://localhost:9696 python benchmarks/recall_latency_bench.py --requests 50 --concurrency 4
```

This ensures that tests validate actual system behavior and catch real integration issues.
