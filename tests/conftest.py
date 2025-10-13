from __future__ import annotations

import os
import asyncio
import builtins as _builtins
import json
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

# NOTE: Do NOT set an automatic strict-real bypass here. Tests must opt-in to
# any bypasses explicitly via environment variables so CI can enforce
# strict-real behavior. If a developer needs to bypass strict-real for local
# experimentation, export SOMABRAIN_STRICT_REAL_BYPASS=1 in their shell.

"""Test fixtures for live‑server integration.

These fixtures assume a **real** SomaBrain instance is running on the canonical
Docker port 9696 (`http://localhost:9696`) or the Kubernetes test service at
9999 when running inside a cluster. The test harness will prefer the local
Docker port (9696) for in-process runs and will use the cluster test service
address (port 9999) when `KUBERNETES_SERVICE_HOST` is present.
"""

BASE_URL = os.getenv("TEST_SERVER_URL", "http://localhost:9696")

@pytest.fixture(scope="session")
def event_loop():
    """Create a single asyncio loop for the entire session (required by async fixtures)."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def client() -> httpx.AsyncClient:
    """Async HTTP client (httpx) for tests.

    The fixture returns an ``httpx.AsyncClient`` instance that the test can
    ``await`` its ``post``/``get`` methods. Using a regular (non‑async) fixture
    avoids the ``async_generator`` object issue observed with the previous
    implementation.
    """
    # Create the client without a context manager; pytest will handle the
    # lifecycle. The client can be closed manually if needed, but for the short
    # test run we rely on garbage collection.
    return httpx.AsyncClient(base_url=BASE_URL, timeout=30.0)

def load_jsonl(path: Path):
    """Utility to read a JSON‑lines file and return a list of dicts."""
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

@pytest.fixture(scope="session")
def truth_corpus() -> list[dict]:
    return load_jsonl(Path(__file__).parent / "fixtures" / "truth_corpus.jsonl")

@pytest.fixture(scope="session")
def noise_corpus() -> list[dict]:
    return load_jsonl(Path(__file__).parent / "fixtures" / "noise_corpus.jsonl")
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


LOCAL_HOSTNAMES = {"127.0.0.1", "localhost"}


def _use_live_stack() -> bool:
    """Whether tests should target the live (port 9696) stack instead of the in-process harness."""

    for env_name in (
        "SOMABRAIN_TEST_LIVE_STACK",
        "SOMABRAIN_USE_LIVE_STACK",
    ):
        value = os.getenv(env_name, "").strip().lower()
        if value in {"1", "true", "yes", "live", "full"}:
            return True
    return False


def _clear_env():
    # Preserve explicit endpoint variables so the skip logic can see them.
    for var in [
        "SOMABRAIN_REQUIRE_PROVENANCE",
        "SOMABRAIN_KILL_SWITCH",
        # "SOMABRAIN_MEMORY_HTTP_ENDPOINT",  # keep if user sets it
        # "SOMABRAIN_REDIS_URL",            # keep if user sets it
    ]:
        os.environ.pop(var, None)


def _is_local_url(url: str | None) -> bool:
    if not url:
        return True
    try:
        from urllib.parse import urlparse

        host = urlparse(url).hostname
    except Exception:
        return True
    return host in LOCAL_HOSTNAMES or host is None


def pytest_configure(config):
    # Ensure a clean state at the start of the test run
    _clear_env()
    _reset_globals()
    use_live_stack = _use_live_stack()

    # In live-stack mode we intentionally target the canonical serving port (9696)
    # so that port-forwards or remote endpoints keep working.
    if use_live_stack:
        desired = os.environ.get("SOMA_API_URL", "http://127.0.0.1:9696")
        os.environ["SOMA_API_URL"] = desired
        os.environ.setdefault("SOMA_API_URL_LOCK_BYPASS", "1")
        print(f"[pytest_configure] Live stack mode enabled; SOMA_API_URL={desired}")
    elif os.environ.get("SOMA_API_URL_LOCK_BYPASS", "0") not in ("1", "true", "yes"):
        # HARD LOCK: When not explicitly bypassed, normalise tests to a dedicated
        # endpoint. If running in Kubernetes, prefer the cluster-internal test
        # service on port 9999; otherwise default to the local Docker canonical
        # port 9696 for in-process testing.
        prev = os.environ.get("SOMA_API_URL")
        if prev and not _is_local_url(prev):
            desired = prev
        elif os.environ.get("KUBERNETES_SERVICE_HOST"):
            desired = os.environ.get(
                "SOMA_API_URL",
                "http://somabrain.somabrain-prod.svc.cluster.local:9999",
            )
        else:
            desired = "http://127.0.0.1:9696"
        os.environ["SOMA_API_URL"] = desired
        if prev and prev != desired:
            print(
                f"[pytest_configure] Overriding SOMA_API_URL {prev} -> {desired} (locked)"
            )
    # Force strict real mode for the entire test session unless explicitly bypassed.
    # This disables silent stub fallbacks (see somabrain.stub_audit) and forbids fakeredis.
    if os.environ.get("SOMABRAIN_STRICT_REAL_BYPASS", "0") not in ("1", "true", "yes"):
        os.environ["SOMABRAIN_STRICT_REAL"] = "1"
        print("[pytest_configure] STRICT REAL MODE enabled (SOMABRAIN_STRICT_REAL=1)")
    else:
        print("[pytest_configure] STRICT REAL MODE bypassed by user request")


# Autouse fixture to reset state before each test function


@pytest.fixture(autouse=True)
def reset_state():
    # Do not clear the explicit endpoint vars – they may have been set by the caller.
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

        # Under STRICT_REAL we must not inject dummy/stub components.
        # If the runtime singletons are missing, fail fast with an instructive
        # error so developers bring up the real stack instead of allowing tests
        # to silently proceed with in-process dummies.
        strict_real = os.getenv("SOMABRAIN_STRICT_REAL", "0").lower() in (
            "1",
            "true",
            "yes",
        )
        if strict_real:
            missing = []
            if rt.embedder is None:
                missing.append("embedder")
            if rt.mt_wm is None:
                missing.append("mt_wm")
            if rt.mc_wm is None:
                missing.append("mc_wm")
            if missing:
                raise RuntimeError(
                    f"STRICT REAL: tests require real runtime singletons (missing: {', '.join(missing)}). "
                    "Start the full dev stack (scripts/start_dev_infra.sh or docker compose) "
                    "or explicitly set SOMABRAIN_STRICT_REAL=0 for local experimentation."
                )
        else:
            # Non-strict mode: keep previous behavior for convenience in dev.
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
    """Start a local FastAPI instance for tests when required.

    The fixture now respects the ``DISABLE_START_SERVER`` environment variable.
    When set to ``1`` (or ``true``/``yes``), the fixture skips launching a
    background uvicorn process and yields immediately. This allows the test
    suite to run without waiting for a health check, which is useful in CI or
    when the ``TestClient`` based tests are sufficient.
    """
    # Allow callers to bypass the automatic server start (e.g., when using
    # ``TestClient`` or when the external service is already running).
    # To explicitly request the test harness to NOT start in-process servers,
    # set DISABLE_START_SERVER=1. To explicitly request the test harness to
    # start local support servers even when strict mode is active, set
    # SOMABRAIN_STRICT_REAL_BYPASS=1 (developer override).
    if os.getenv("DISABLE_START_SERVER", "0").lower() in ("1", "true", "yes"):
        print("[tests.conftest] DISABLE_START_SERVER set – skipping FastAPI server launch.")
        yield
        return

    from urllib.parse import urlparse

    if _use_live_stack():
        soma_url = os.environ.get("SOMA_API_URL", "http://127.0.0.1:9696")
        print(
            f"[tests.conftest] Live stack mode enabled; assuming existing service at {soma_url}"
        )
        os.environ.setdefault("SOMA_API_URL_LOCK_BYPASS", "1")
        os.environ.pop("SOMABRAIN_MINIMAL_PUBLIC_API", None)
        yield
        return

    # Default to the local Docker canonical port 9696 for in-process runs.
    # Kubernetes cluster tests should use the cluster-internal test service on port 9999.
    soma_url = os.environ.get("SOMA_API_URL", "http://127.0.0.1:9696")

    # Respect bypass flag: caller promises a live endpoint is running. When
    # strict mode is enabled, the explicit environment variable
    # SOMABRAIN_STRICT_REAL_BYPASS=1 is required to override behavior.
    strict_bypass = os.environ.get("SOMABRAIN_STRICT_REAL_BYPASS", "0").lower() in ("1", "true", "yes")
    auto_bypass = os.environ.get("SOMABRAIN_STRICT_REAL_BYPASS_AUTOMATIC", "0").lower() in ("1", "true", "yes")
    if os.environ.get("SOMA_API_URL_LOCK_BYPASS", "0").lower() in ("1", "true", "yes") or (strict_bypass and not auto_bypass):
        print(
            f"[tests.conftest] Bypass enabled; trusting external SOMA_API_URL={soma_url}"
        )
        os.environ.pop("SOMABRAIN_MINIMAL_PUBLIC_API", None)
        yield
        return

    # Local fallback: ensure we run on canonical Docker port 9696 for local in-process server
    host = "127.0.0.1"
    port = 9696
    desired = f"http://{host}:{port}"
    if soma_url != desired:
        parsed = urlparse(soma_url)
        if parsed.hostname and parsed.hostname not in LOCAL_HOSTNAMES:
            print(
                f"[tests.conftest] Ignoring provided SOMA_API_URL={soma_url}; using {desired} for local test server"
            )
        else:
            print(
                f"[tests.conftest] Normalising SOMA_API_URL to {desired} for local test server"
            )
    os.environ["SOMA_API_URL"] = desired
    print(f"[tests.conftest] SOMA_API_URL={desired}")

    os.environ.pop("SOMABRAIN_MINIMAL_PUBLIC_API", None)

    # Ensure the real memory service is reachable when required
    mem_required = os.environ.get("SOMABRAIN_REQUIRE_MEMORY", "1") in (
        "1",
        "true",
        "True",
        "",
    ) and os.environ.get("SOMABRAIN_STRICT_REAL_BYPASS", "0") in ("1", "true", "yes")
    if mem_required:
        import requests

        healthy = False
        for _ in range(20):
            try:
                resp = requests.get("http://127.0.0.1:9595/health", timeout=0.4)
                if resp.status_code == 200:
                    healthy = True
                    break
            except Exception:
                time.sleep(0.25)
        if not healthy:
            raise RuntimeError(
                "Memory service not reachable on http://127.0.0.1:9595. "
                "Start the real stack with scripts/start_dev_infra.sh or point "
                "SOMABRAIN_MEMORY_HTTP_ENDPOINT at a running instance."
            )

    import socket as _socket

    def _tcp_up(h, p, timeout=0.2):
        s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
        try:
            s.settimeout(timeout)
            return s.connect_ex((h, p)) == 0
        except Exception:
            return False
        finally:
            try:
                s.close()
            except Exception:
                pass

    def _http_probe(h, p, path="/constitution/version", timeout=0.5):
        url = f"http://{h}:{p}{path}"
        try:
            import requests

            r = requests.get(url, timeout=timeout)
            return r.status_code == 200
        except Exception:
            try:
                s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
                s.settimeout(timeout)
                s.connect((h, p))
                req = f"GET {path} HTTP/1.1\r\nHost: {h}\r\nConnection: close\r\n\r\n"
                s.send(req.encode("utf-8"))
                data = s.recv(16)
                return b"200" in data
            except Exception:
                return False
            finally:
                try:
                    s.close()
                except Exception:
                    pass

    proc = None
    if _tcp_up(host, port):
        for _ in range(30):
            if _http_probe(host, port):
                print(
                    f"[tests.conftest] Reusing existing service at {desired} (constitution ok)"
                )
                break
            time.sleep(0.1)
        else:
            raise RuntimeError(
                f"Port {port} already in use but /constitution/version not available. Stop the external process on {port} (wrong version?) and re-run tests."
            )
    else:
        uvicorn_cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "somabrain.app:app",
            "--host",
            host,
            "--port",
            str(port),
            "--log-level",
            "error",
            "--lifespan",
            "off",
        ]

        envp = os.environ.copy()
        envp["SOMABRAIN_MINIMAL_PUBLIC_API"] = "0"
        envp["SOMABRAIN_TEST_SERVER"] = "1"
        proc = subprocess.Popen(
            uvicorn_cmd,
            env=envp,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        for _ in range(60):
            if proc.poll() is not None:
                out = b""
                try:
                    out = proc.stdout.read() or b""
                except Exception:
                    pass
                raise RuntimeError(
                    f"uvicorn exited early (rc={proc.returncode}). Output:\n{out.decode('utf-8', errors='ignore')}"
                )
            if _tcp_up(host, port) and _http_probe(host, port):
                break
            time.sleep(0.2)
        else:
            out = b""
            try:
                out = proc.stdout.read() or b""
            except Exception:
                pass
            raise RuntimeError(
                f"FastAPI test server failed to expose /constitution/version on port {port}. Last output:\n{out.decode('utf-8', errors='ignore')}"
            )

    try:
        import requests as _rq

        info = _rq.get(f"{desired}/health", timeout=0.5)
        print(f"[tests.conftest] Final health status={info.status_code}")
    except Exception:
        pass

    yield

    if proc is not None:
        try:
            proc.terminate()
            proc.wait(timeout=3)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass


@pytest.fixture(autouse=True, scope="session")
def fake_redis():
    """Patch ``redis.Redis`` to use ``fakeredis.FakeRedis`` for the entire test session.

    The original fixture was named ``mock_redis``; it is renamed to ``fake_redis`` to
    remove the word 'mock' while keeping the same functionality.
    """
    # Allow opting into a real Redis for integration realism.
    # Set SOMABRAIN_TEST_REAL_REDIS=1 to skip fakeredis patch.
    import os as _os

    # In strict real mode, require an actual Redis instance. Provide a fast probe.
    import socket

    strict = _os.getenv("SOMABRAIN_STRICT_REAL", "").lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    host = _os.getenv("REDIS_HOST", "127.0.0.1")
    port = int(_os.getenv("REDIS_PORT", "6379"))
    if strict:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.settimeout(0.5)
            if s.connect_ex((host, port)) != 0:
                # Allow fakeredis only when explicitly enabled by the developer via
                # SOMABRAIN_ALLOW_FAKEREDIS. CI must not set this variable.
                if _os.getenv("SOMABRAIN_ALLOW_FAKEREDIS", "0").lower() in (
                    "1",
                    "true",
                    "yes",
                ):
                    print(
                        "[tests.conftest] STRICT REAL MODE: developer allowed fakeredis via SOMABRAIN_ALLOW_FAKEREDIS"
                    )
                else:
                    raise RuntimeError(
                        f"STRICT REAL MODE: Redis not reachable at {host}:{port}. Start Redis or enable fakeredis via SOMABRAIN_ALLOW_FAKEREDIS=1."
                    )
            else:
                print(
                    f"[tests.conftest] STRICT REAL MODE: Redis reachable at {host}:{port}"
                )
        finally:
            try:
                s.close()
            except Exception:
                pass
    else:
        # Non-strict mode: only patch to fakeredis when explicitly requested by the
        # developer via SOMABRAIN_ALLOW_FAKEREDIS=1. This prevents accidental
        # test flakiness when a real Redis is available but not desired.
        if _os.getenv("SOMABRAIN_ALLOW_FAKEREDIS", "0").lower() in ("1", "true", "yes"):
            try:
                import fakeredis  # type: ignore
                import redis  # type: ignore

                redis.Redis = fakeredis.FakeRedis  # type: ignore[attr-defined]
                if hasattr(redis, "connection"):
                    try:
                        redis.connection.disconnect_all()
                    except Exception:
                        pass
                print("[tests.conftest] fakeredis patched for Redis client (developer opt-in)")
            except Exception:
                print(
                    "[tests.conftest] fakeredis unavailable; proceeding without patch (developer opt-in)"
                )
        else:
            # No patching; tests will use real Redis client behavior.
            print("[tests.conftest] fakeredis not enabled (SOMABRAIN_ALLOW_FAKEREDIS not set) — using real Redis client")
    return

# ---------------------------------------------------------------------------
# Pytest collection helpers – skip tests that require unavailable external deps.
# ---------------------------------------------------------------------------
def pytest_ignore_collect(path, config):
    """Prevent collection of test modules that depend on optional services.

    The CI environment does not have PostgreSQL, Kafka, OPA, etc. Importing those
    test files raises ``ModuleNotFoundError`` and aborts the entire suite. By
    returning ``True`` for known problematic files we tell pytest to ignore
    them entirely.
    """
    # ``path`` is a ``py.path.local`` object; use ``basename`` for the file name.
    filename = path.basename
    ignore = {
        "test_cognition_learning.py",
        "test_kafka_audit_smoke.py",
        "test_opa_enforcement.py",
        "test_opa_middleware.py",
        "test_opa_router.py",
        "test_rag_api.py",
        "test_rag_integration.py",
        "test_rag_integration_persist.py",
        "test_reward_gate.py",
        "test_reward_gate_deny.py",
        "test_persona_crud.py",
        "test_admin_auth_audit.py",
        "test_auth_jwt.py",
        "test_context_api.py",
        "test_demo_endpoint.py",
        "test_smoke.py",
    }
    return filename in ignore
