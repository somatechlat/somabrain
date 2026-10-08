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
    "SOMA_DB_HOST": "127.0.0.1",
    "SOMA_DB_PORT": "63932",
    "SOMA_DB_USER": "soma",
    "SOMA_DB_PASSWORD": "soma",
    "SOMA_DB_NAME": "somabrain",
    # Redis (somastack_redis)
    "SOMA_REDIS_HOST": "127.0.0.1",
    "SOMA_REDIS_PORT": "63979",
    # Milvus (somastack_milvus)
    "SOMA_MILVUS_HOST": "127.0.0.1",
    "SOMA_MILVUS_PORT": "63953",
    # Kafka (somastack_kafka)
    "KAFKA_BOOTSTRAP_SERVERS": "127.0.0.1:63992",
    # Mode flags
    "SOMA_AAAS_MODE": "true",
    "SA01_DEPLOYMENT_MODE": "AAAS",
}

STANDALONE_ENV = {
    "SOMA_DB_HOST": "127.0.0.1",
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
    """Register custom markers and seed test-only secret state."""
    config.addinivalue_line("markers", "aaas: AAAS mode tests (requires Docker infra)")
    config.addinivalue_line("markers", "standalone: Standalone mode tests")
    config.addinivalue_line("markers", "slow: Long-running tests")
    config.addinivalue_line("markers", "infra: Requires real infrastructure")
    config.addinivalue_line("markers", "unit: Pure unit tests (no infrastructure)")
    config.addinivalue_line(
        "markers",
        "no_django: test covers a Django-free package and must not boot settings",
    )
    # Pre-seed somabrain.settings.infra._RESOLVED with test-only secret state
    # so the Django settings chain can import without a live Vault.  The infra
    # module is loaded from its file (bypassing the package __init__ chain that
    # runs credential gates) and registered under its real dotted name so the
    # subsequent normal import reuses this module object and its state.
    try:
        import importlib.util as _ilu
        import sys as _sys
        from pathlib import Path as _Path

        _infra_key = "somabrain.settings.infra"
        if _infra_key not in _sys.modules:
            _infra_path = (
                _Path(__file__).resolve().parent.parent
                / "somabrain"
                / "settings"
                / "infra.py"
            )
            _spec = _ilu.spec_from_file_location(_infra_key, str(_infra_path))
            if _spec and _spec.loader:
                _mod = _ilu.module_from_spec(_spec)
                _sys.modules[_infra_key] = _mod
                _spec.loader.exec_module(_mod)
                # Seed test-only secrets before any credential gate reads them.
                _mod._RESOLVED.setdefault(
                    "SOMABRAIN_MEMORY_HTTP_TOKEN", "test-only-token"
                )
                _mod._RESOLVED.setdefault("POSTGRES_PASSWORD", "test-only-password")
                _mod._RESOLVED.setdefault(
                    "SOMABRAIN_PROVENANCE_SECRET", "test-only-provenance"
                )
                # The module-level constants were computed from the empty
                # _RESOLVED dict during exec_module.  Refresh them now.
                _mod.SOMABRAIN_MEMORY_HTTP_TOKEN = "test-only-token"
                _mod.SOMABRAIN_PROVENANCE_SECRET = "test-only-provenance"
    except Exception:
        pass

    # Boot the full somabrain.settings chain once, before any test module
    # import. A later ``dj_settings.configure(minimal_dict)`` from a
    # ``no_django`` file would replace this and break SLEEP_K0 / neuro
    # attributes for every subsequent suite (test isolation).
    try:
        _ensure_django()
    except Exception:
        pass


_DJANGO_READY = False


def _ensure_django() -> None:
    """Boot Django settings once, for the tests that need them."""
    global _DJANGO_READY
    if _DJANGO_READY:
        return
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "somabrain.settings")
    import django

    django.setup()
    _DJANGO_READY = True


@pytest.fixture(autouse=True)
def configure_test_environment(request):
    """Boot Django settings before each test that needs them.

    Marked ``no_django`` tests are skipped entirely here. Those cover packages
    built to be Django-free — ``somabrain.transport`` is one — and booting
    settings for them would couple a pure transport test to the memory-HTTP
    credential gate, which that test neither uses nor can satisfy.
    """
    if request.node.get_closest_marker("no_django") is not None:
        return
    _ensure_django()


@pytest.fixture(autouse=True)
def init_brain_settings(request):
    """Initialize brain settings only for tests that explicitly use the database."""
    if request.node.get_closest_marker("django_db") is None:
        return

    request.getfixturevalue("db")
    from somabrain.brain_settings.models import BrainSetting

    from somabrain.brain_settings.models import _base_profile
    BrainSetting.initialize_defaults(_base_profile())


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

    host = os.environ.get("SOMA_DB_HOST", "127.0.0.1")
    port = int(os.environ.get("SOMA_DB_PORT", "63932"))
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except (TimeoutError, OSError):
        pytest.skip(f"PostgreSQL not available at {host}:{port}")


@pytest.fixture(scope="session")
def milvus_available():
    """Check if Milvus is available."""
    import socket

    host = os.environ.get("SOMA_MILVUS_HOST", "127.0.0.1")
    port = int(os.environ.get("SOMA_MILVUS_PORT", "63953"))
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except (TimeoutError, OSError):
        pytest.skip(f"Milvus not available at {host}:{port}")


@pytest.fixture(scope="session")
def redis_available():
    """Check if Redis is available."""
    import socket

    host = os.environ.get("SOMA_REDIS_HOST", "127.0.0.1")
    port = int(os.environ.get("SOMA_REDIS_PORT", "63979"))
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except (TimeoutError, OSError):
        pytest.skip(f"Redis not available at {host}:{port}")


@pytest.fixture(scope="session")
def kafka_available():
    """Check if Kafka is available."""
    import socket

    try:
        with socket.create_connection(("127.0.0.1", 63992), timeout=2):
            return True
    except (TimeoutError, OSError):
        pytest.skip("Kafka not available at 127.0.0.1:63992")
