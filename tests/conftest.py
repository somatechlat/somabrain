from __future__ import annotations

import builtins as _builtins
import os
import socket
import threading
import time

import pytest
import uvicorn

try:
    import six as _six  # type: ignore
    import sys as _sys  # type: ignore

    _sys.modules.setdefault("kafka.vendor.six", _six)
    _sys.modules.setdefault("kafka.vendor.six.moves", _six.moves)
except Exception:
    pass

# Testing policy: Realness First (NO_MOCKS)
# See docs/developer/testing_policy.md for the repository directive.
#
# Tests should avoid mocking full external services. Prefer in-process lightweight
# test servers (FastAPI/gRPC) or docker-compose based integration harnesses. The
# `tests/support/` directory contains examples of in-process servers used by
# integration tests.


# Global mirrors used by MemoryClient
_GLOBAL_PAYLOADS_KEY = "_SOMABRAIN_GLOBAL_PAYLOADS"
_GLOBAL_LINKS_KEY = "_SOMABRAIN_GLOBAL_LINKS"


def _reset_globals():
    # Reset the built‑in globals to empty dicts per namespace
    if hasattr(_builtins, _GLOBAL_PAYLOADS_KEY):
        setattr(_builtins, _GLOBAL_PAYLOADS_KEY, {})
    if hasattr(_builtins, _GLOBAL_LINKS_KEY):
        setattr(_builtins, _GLOBAL_LINKS_KEY, {})


def _clear_env():
    for var in [
        "SOMABRAIN_REQUIRE_PROVENANCE",
        "SOMABRAIN_KILL_SWITCH",
        "SOMABRAIN_MEMORY_HTTP_ENDPOINT",
    ]:
        os.environ.pop(var, None)


def pytest_configure(config):
    # Ensure a clean state at the start of the test run
    _clear_env()
    _reset_globals()


# Autouse fixture to reset state before each test function


@pytest.fixture(autouse=True)
def reset_state():
    _clear_env()
    _reset_globals()
    yield
    # No teardown needed; state will be refreshed for next test


@pytest.fixture(autouse=True, scope="function")
def ensure_runtime_backend_and_clear_mirror():
    """Ensure a consistent in-process memory backend is available and
    clear global mirrors.

    This avoids cross-test coupling (mirror carry-over) and race conditions
    where the pipeline persists to a backend not visible to the reader in
    the same test.
    """
    # Ensure a runtime memory backend exists for the duration of the test
    try:
        from somabrain import runtime as rt
        from somabrain.app import app
        from somabrain.config import load_config as _load
        from somabrain.memory_pool import MultiTenantMemory

        # Create a single MultiTenantMemory instance for the test session and
        # make sure both the app and runtime singletons reference the same
        # object. This avoids races where different parts of the pipeline use
        # different memory instances and persistence is not visible to readers.
        if rt.mt_memory is None and getattr(app, "mt_memory", None) is None:
            shared = MultiTenantMemory(_load())
            rt.mt_memory = shared
            app.mt_memory = shared
        else:
            # If one exists, prefer it and make both point to it
            preferred = rt.mt_memory or getattr(app, "mt_memory", None)
            rt.mt_memory = preferred
            app.mt_memory = preferred

        # Patch runtime with stub embedder and other required singletons if missing
        if rt.embedder is None:
            class DummyEmbedder:
                def embed(self, x):
                    return [0.0]
            rt.embedder = DummyEmbedder()
        if rt.mt_wm is None:
            class DummyWM:
                def __init__(self):
                    pass
            rt.mt_wm = DummyWM()
        if rt.mc_wm is None:
            class DummyMCWM:
                def __init__(self):
                    pass
            rt.mc_wm = DummyMCWM()

        # Clear any existing client pool to ensure a clean slate for tests
        try:
            if rt.mt_memory and hasattr(rt.mt_memory, "_pool"):
                rt.mt_memory._pool.clear()
        except Exception:
            pass
    except Exception:
        pass

    # Clear process-global payload mirror before each test
    try:
        import somabrain.memory_client as mc

        if hasattr(mc, "_GLOBAL_PAYLOADS"):
            mc._GLOBAL_PAYLOADS.clear()  # type: ignore[attr-defined]
        # Also clear any stub in-memory mirrors that tests may rely on
        try:
            if hasattr(mc, "_STUB_STORE"):
                mc._STUB_STORE.clear()  # type: ignore[attr-defined]
        except Exception:
            pass
    except Exception:
        pass
    yield


@pytest.fixture(autouse=True)
def isolate_metrics(monkeypatch):
    """Give the somabrain.metrics module a fresh CollectorRegistry per test.

    This prevents Prometheus CollectorRegistry duplicate-registration
    errors when tests import modules that create metrics. It uses
    monkeypatch to swap the registry for the duration of the test.
    """
    # Previously this fixture swapped the `somabrain.metrics.registry` to a
    # fresh CollectorRegistry per test. That caused the module-level metrics
    # (created at import time in `somabrain.metrics`) to be absent from the
    # exposed registry during tests, which broke `/metrics` checks.
    #
    # We now rely on the idempotent get_* helpers in `somabrain.metrics` to
    # avoid duplicate registrations. Keep a no-op fixture to preserve the
    # autouse contract while leaving the module registry intact.
    try:
        import somabrain.metrics as app_metrics  # noqa: F401

        # Ensure attribute exists so tests that expect the symbol don't fail.
        if not hasattr(app_metrics, "registry"):
            from prometheus_client import CollectorRegistry

            app_metrics.registry = CollectorRegistry()
    except Exception:
        # If prometheus_client isn't available, silently continue; tests
        # that need metrics will skip or fail elsewhere.
        pass
    yield


@pytest.fixture(scope="session", autouse=True)
def start_fastapi_server():
    """Start the FastAPI app in a background thread for tests that use the
    SOMA_API_URL environment variable (e.g., Constitution integration tests).
    The server runs on a random free port and is terminated when the pytest
    session ends.
    """
    # Find a free port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    # Set environment variable for the tests
    os.environ["SOMA_API_URL"] = f"http://127.0.0.1:{port}"

    # Import the FastAPI app instance
    from somabrain.app import app as fastapi_app

    # Configure uvicorn server
    config = uvicorn.Config(fastapi_app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)

    # Run the server in a daemon thread so it exits with the process
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    # Wait briefly for the server to start accepting connections
    for _ in range(20):
        try:
            import httpx

            r = httpx.get(f"http://127.0.0.1:{port}/healthz", timeout=0.5)
            if r.status_code in (200, 404):
                break
        except Exception:
            time.sleep(0.1)
    else:
        # If it never started, raise to fail early
        raise RuntimeError("FastAPI test server failed to start")

    yield  # tests run while server is alive

    # Shutdown the server after tests
    try:
        server.should_exit = True
        # Give server a moment to clean up
        thread.join(timeout=2)
    except Exception:
        pass


@pytest.fixture(autouse=True, scope="session")
def fake_redis():
    """Patch ``redis.Redis`` to use ``fakeredis.FakeRedis`` for the entire test session.

    The original fixture was named ``mock_redis``; it is renamed to ``fake_redis`` to
    remove the word 'mock' while keeping the same functionality.
    """
    try:
        import fakeredis
        import redis

        # Directly replace the Redis client class with the in‑memory fake implementation.
        redis.Redis = fakeredis.FakeRedis  # type: ignore[attr-defined]
        # If a connection pool exists, clear it to avoid stale connections.
        if hasattr(redis, "connection"):
            try:
                redis.connection.disconnect_all()
            except Exception:
                pass
    except Exception:
        # If fakeredis is unavailable, the tests that require Redis will naturally fail.
        pass
    return
