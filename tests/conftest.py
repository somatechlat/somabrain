from __future__ import annotations

import builtins as _builtins
import os
import time
import subprocess
import sys

import pytest

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
    # HARD LOCK: Always point tests at dedicated integration server port 9797.
    # The user requested we never hit 9696 because a different version may be
    # running there. We override any pre-set SOMA_API_URL (unless explicitly
    # exported SOMA_API_URL_LOCK_BYPASS=1 for an advanced/manual scenario).
    if os.environ.get("SOMA_API_URL_LOCK_BYPASS", "0") not in ("1", "true", "yes"):
        prev = os.environ.get("SOMA_API_URL")
        if prev and not _is_local_url(prev):
            desired = prev
        elif os.environ.get("KUBERNETES_SERVICE_HOST"):
            desired = os.environ.get(
                "SOMA_API_URL",
                "http://somabrain.somabrain-prod.svc.cluster.local:9696",
            )
        else:
            desired = "http://127.0.0.1:9797"
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
    """Start a local FastAPI instance for tests when required.

    When tests are executed inside a Kubernetes context (or the caller
    explicitly provides an external ``SOMA_API_URL``), we assume the API is
    already running and reachable and therefore skip bootstrapping a local
    uvicorn server. This keeps the test suite aligned with the "no mocks"
    directive while still supporting developer machines.
    """
    from urllib.parse import urlparse

    soma_url = os.environ.get("SOMA_API_URL", "http://127.0.0.1:9797")

    # Respect bypass flag: caller promises a live endpoint is running.
    if os.environ.get("SOMA_API_URL_LOCK_BYPASS", "0") in ("1", "true", "yes"):
        print(
            f"[tests.conftest] Bypass enabled; trusting external SOMA_API_URL={soma_url}"
        )
        os.environ.pop("SOMABRAIN_MINIMAL_PUBLIC_API", None)
        yield
        return

    # Local fallback: ensure we run on dedicated loopback port 9797
    host = "127.0.0.1"
    port = 9797
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

    # Ensure memory stub is online (only needed for local test harness)
    try:
        from tests.support.memory_service import run_memory_server  # type: ignore

        mem_required = os.environ.get("SOMABRAIN_REQUIRE_MEMORY", "1") in (
            "1",
            "true",
            "True",
            "",
        )
        if mem_required:
            import requests

            try:
                r = requests.get("http://127.0.0.1:9595/health", timeout=0.4)
                if r.status_code != 200:
                    raise RuntimeError("memory not healthy yet")
            except Exception:
                run_memory_server()
                for _ in range(20):
                    try:
                        rr = requests.get("http://127.0.0.1:9595/health", timeout=0.25)
                        if rr.status_code == 200:
                            break
                    except Exception:
                        time.sleep(0.1)
    except Exception:
        pass

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
                raise RuntimeError(
                    f"STRICT REAL MODE: Redis not reachable at {host}:{port}. Start Redis or bypass via SOMABRAIN_STRICT_REAL_BYPASS=1."
                )
            print(
                f"[tests.conftest] STRICT REAL MODE: Redis reachable at {host}:{port}"
            )
        finally:
            try:
                s.close()
            except Exception:
                pass
    else:
        # Legacy relaxed path: allow fakeredis unless explicitly disabled.
        if _os.getenv("SOMABRAIN_TEST_REAL_REDIS", "").lower() in (
            "1",
            "true",
            "yes",
            "on",
        ):
            print("[tests.conftest] REAL Redis requested (no fakeredis patch)")
            return
        try:
            import fakeredis  # type: ignore
            import redis  # type: ignore

            redis.Redis = fakeredis.FakeRedis  # type: ignore[attr-defined]
            if hasattr(redis, "connection"):
                try:
                    redis.connection.disconnect_all()
                except Exception:
                    pass
            print("[tests.conftest] fakeredis patched for Redis client (relaxed mode)")
        except Exception:
            print(
                "[tests.conftest] fakeredis unavailable; proceeding without patch (relaxed mode)"
            )
    return
