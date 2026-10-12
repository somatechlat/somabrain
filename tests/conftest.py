"""Unified Test Configuration - SomaBrain

VIBE Coding Rules Compliant:
- Real infrastructure only (NO mocks)
- Soma Platform/Standalone mode separation
- Centralized environment configuration

Test Structure:
- tests/platform/      - SOMA_AAAS_MODE=true tests
- tests/standalone/ - SOMA_AAAS_MODE=false tests
- tests/unit/      - Pure unit tests (no infra)
- tests/integration/ - Cross-service tests
- tests/e2e/       - Full end-to-end flows
"""

import os

import pytest

# ===========================================================================
# ENVIRONMENT CONFIGURATION - Soma Platform INFRASTRUCTURE (Port 639xx)
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
    "SA01_DEPLOYMENT_MODE": "Soma Platform",
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
    config.addinivalue_line("markers", "platform: Soma Platform mode tests (requires Docker infra)")
    config.addinivalue_line("markers", "standalone: Standalone mode tests")
    config.addinivalue_line("markers", "slow: Long-running tests")
    config.addinivalue_line("markers", "infra: Requires real infrastructure")
    config.addinivalue_line("markers", "unit: Pure unit tests (no infrastructure)")
    config.addinivalue_line(
        "markers",
        "no_django: test covers a Django-free package and must not boot settings",
    )
    # Seed test-only secret state so the Django settings chain can import
    # without a live Vault. Credential gates run at import time
    # (settings/infra.py, settings/django_core.py) and refuse empty secrets.
    # A stand-in vault_client answers those lookups with test-only values for
    # the duration of the boot only; real Vault readers are restored after.
    # Production secrets never land in os.environ (Rule 164).
    #
    # REAL-INFRA MODE: when live Vault topology is present (VAULT_ADDR +
    # VAULT_TOKEN_FILE), do NOT install the stub. The production vault_client
    # resolves real credentials from Vault, so tests exercise the real path.
    # Topology (hosts / allow-list) stays on ENV — that is the lawful channel.
    # Always set, even in real-Vault mode: settings refuse empty ALLOWED_HOSTS.
    os.environ.setdefault("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver")
    os.environ.setdefault("SOMABRAIN_NAMESPACE", "test-ns")
    os.environ.setdefault("SOMABRAIN_HOST", "127.0.0.1")
    os.environ.setdefault("SOMABRAIN_PORT", "30101")
    _real_vault = bool(
        os.environ.get("VAULT_ADDR")
        and os.environ.get("VAULT_TOKEN_FILE")
        and os.path.isfile(os.environ.get("VAULT_TOKEN_FILE", ""))
    )
    if _real_vault:
        # Real Vault: production vault_client resolves credentials. Still boot
        # Django so models/apps are ready for django_db tests.
        try:
            _ensure_django()
        except Exception:
            pass
        return
    try:
        import sys as _sys
        import types as _types

        _vc_key = "somabrain.core.security.vault_client"
        _real_vc = _sys.modules.get(_vc_key)
        _vc = _types.ModuleType(_vc_key)

        class _SecretNotFound(Exception):
            pass

        class _VaultNotConfigured(Exception):
            pass

        class _VaultAuthError(Exception):
            pass

        _vc.SecretNotFound = _SecretNotFound
        _vc.VaultNotConfigured = _VaultNotConfigured
        _vc.VaultAuthError = _VaultAuthError
        _vc.get_db_credentials = lambda: {
            "username": "test",
            "password": "test-only-password",
            "host": "127.0.0.1",
            "port": "5432",
            "dbname": "somabrain",
        }
        _vc.get_secret = lambda path, key=None: (
            "test-only-token" if key else {"k": "test-only-token"}
        )
        _vc.get_jwt_secret = lambda: "test-only-jwt-secret"
        _vc.get_runtime_secrets = lambda: {
            "memory_http_token": "test-only-token",
            "provenance_secret": "test-only-provenance",
            "api_token": "test-only-token",
            "supervisor_http_pass": "test-only-supervisor",
        }
        _vc.get_runtime_secret = lambda key: "test-only-token"
        _vc.get_api_key = lambda service: "test-only-token"
        _sys.modules[_vc_key] = _vc
        try:
            # Boot the full somabrain.settings chain once, before any test
            # module import. A later ``dj_settings.configure(minimal_dict)``
            # from a ``no_django`` file would replace this and break SLEEP_K0
            # / neuro attributes for every subsequent suite.
            _ensure_django()
        finally:
            if _real_vc is not None:
                _sys.modules[_vc_key] = _real_vc
            else:
                _sys.modules.pop(_vc_key, None)
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
    # Override DATABASES with the host-reachable test DSN. The Vault doc uses
    # in-network hostnames (somabrain_standalone_postgres) that do not resolve
    # from the host test runner. This must run AFTER django.setup() so it wins
    # over configure_vault_secrets().
    _dsn = os.environ.get("TEST_PG_DSN", "")
    if _dsn:
        try:
            import urllib.parse as _up

            if _dsn.startswith("postgresql://") or _dsn.startswith("postgres://"):
                _u = _up.urlparse(_dsn)
                from django.conf import settings as _settings

                _settings.DATABASES["default"].update(
                    {
                        "HOST": _u.hostname or "127.0.0.1",
                        "PORT": str(_u.port or 5432),
                        "USER": _u.username or "",
                        "PASSWORD": _u.password or "",
                        "NAME": (_u.path or "/somabrain").lstrip("/"),
                        "ATOMIC_REQUESTS": False,
                        "AUTOCOMMIT": True,
                        "CONN_MAX_AGE": 0,
                        "CONN_HEALTH_CHECKS": False,
                        "OPTIONS": {},
                        "TEST": {"NAME": "test_somabrain"},
                        "MIRROR": None,
                    }
                )
                from django.db import connections as _connections

                _connections.close_all()
        except Exception:
            pass


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
    """Fixture to ensure Soma Platform mode environment."""
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
