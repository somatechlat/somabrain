"""Unified Test Configuration - SomaBrain

VIBE Coding Rules Compliant:
- Real infrastructure only (NO mocks)
- AAAS/Standalone mode separation
- Centralized environment configuration

Test Structure:
- tests/aaas/      - SOMA_AAAS_MODE=true tests
- tests/standalone/ - SOMA_AAAS_MODE=false tests
- tests/unit/      - Pure unit tests (no infra)
- tests/integration/ - Cross-service tests
- tests/e2e/       - Full end-to-end flows
"""

import os
import pytest

# ===========================================================================
# ENVIRONMENT CONFIGURATION - AAAS INFRASTRUCTURE (Port 639xx)
# ===========================================================================

AAAS_ENV = {
    # PostgreSQL (somastack_postgres)
    "SOMA_DB_HOST": "localhost",
    "SOMA_DB_PORT": "63932",
    "SOMA_DB_USER": "soma",
    "SOMA_DB_PASSWORD": "soma",
    "SOMA_DB_NAME": "somabrain",
    # Redis (somastack_redis)
    "SOMA_REDIS_HOST": "localhost",
    "SOMA_REDIS_PORT": "63979",
    # Milvus (somastack_milvus)
    "SOMA_MILVUS_HOST": "localhost",
    "SOMA_MILVUS_PORT": "63953",
    # Kafka (somastack_kafka)
    "KAFKA_BOOTSTRAP_SERVERS": "localhost:63992",
    # Mode flags
    "SOMA_AAAS_MODE": "true",
    "SA01_DEPLOYMENT_MODE": "AAAS",
}

STANDALONE_ENV = {
    "SOMA_DB_HOST": "localhost",
    "SOMA_DB_PORT": "5432",
    "SOMA_MILVUS_PORT": "19530",
    "SOMA_REDIS_PORT": "6379",
    "SOMA_AAAS_MODE": "false",
    "SA01_DEPLOYMENT_MODE": "STANDALONE",
}


def _apply_env(env_dict: dict) -> None:
    """Apply environment variables."""
    for key, value in env_dict.items():
        os.environ[key] = value


# ===========================================================================
# PYTEST CONFIGURATION
# ===========================================================================

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "aaas: AAAS mode tests (requires Docker infra)")
    config.addinivalue_line("markers", "standalone: Standalone mode tests")
    config.addinivalue_line("markers", "slow: Long-running tests")
    config.addinivalue_line("markers", "infra: Requires real infrastructure")
    config.addinivalue_line("markers", "unit: Pure unit tests (no infrastructure)")


@pytest.fixture(scope="session", autouse=True)
def configure_test_environment(request):
    """Auto-configure environment based on test markers."""
    # Default to AAAS mode for integration tests
    _apply_env(AAAS_ENV)

    # Setup Django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "somabrain.settings")
    import django
    django.setup()


@pytest.fixture
def aaas_mode():
    """Fixture to ensure AAAS mode environment."""
    _apply_env(AAAS_ENV)
    yield


@pytest.fixture
def standalone_mode():
    """Fixture to ensure Standalone mode environment."""
    _apply_env(STANDALONE_ENV)
    yield


# ===========================================================================
# INFRASTRUCTURE HEALTH CHECKS
# ===========================================================================

@pytest.fixture(scope="session")
def postgres_available():
    """Check if PostgreSQL is available."""
    import socket
    host = os.environ.get("SOMA_DB_HOST", "localhost")
    port = int(os.environ.get("SOMA_DB_PORT", "63932"))
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except (socket.error, socket.timeout):
        pytest.skip(f"PostgreSQL not available at {host}:{port}")


@pytest.fixture(scope="session")
def milvus_available():
    """Check if Milvus is available."""
    import socket
    host = os.environ.get("SOMA_MILVUS_HOST", "localhost")
    port = int(os.environ.get("SOMA_MILVUS_PORT", "63953"))
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except (socket.error, socket.timeout):
        pytest.skip(f"Milvus not available at {host}:{port}")


@pytest.fixture(scope="session")
def redis_available():
    """Check if Redis is available."""
    import socket
    host = os.environ.get("SOMA_REDIS_HOST", "localhost")
    port = int(os.environ.get("SOMA_REDIS_PORT", "63979"))
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except (socket.error, socket.timeout):
        pytest.skip(f"Redis not available at {host}:{port}")


@pytest.fixture(scope="session")
def kafka_available():
    """Check if Kafka is available."""
    import socket
    try:
        with socket.create_connection(("localhost", 63992), timeout=2):
            return True
    except (socket.error, socket.timeout):
        pytest.skip("Kafka not available at localhost:63992")
