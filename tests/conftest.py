from __future__ import annotations

"""Unified pytest configuration for centralized test suite.

Responsibilities:
 - Load environment variables from `.env` for host-run tests.
 - Auto-mark integration/benchmark tests heuristically by path.
 - Skip performance/benchmark tests unless explicitly requested.
 - Inject infra readiness fixture for integration tests.
 - Normalize service hostnames for local execution.
"""

import os
import subprocess
import sys
import json
from pathlib import Path
from typing import Dict, List
import pytest


def _parse_env_file(path: Path) -> Dict[str, str]:
    env: Dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return env
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip()
        # Strip optional surrounding quotes
        if (v.startswith('"') and v.endswith('"')) or (
            v.startswith("'") and v.endswith("'")
        ):
            v = v[1:-1]
        env[k] = v
    return env


def _bootstrap_env_from_dotenv() -> None:
    root = Path(__file__).resolve().parents[1]
    # Load canonical .env only
    dotenv = root / ".env"
    if dotenv.exists():
        loaded = _parse_env_file(dotenv)
        # Only set variables that are not already defined in the environment
        for k, v in loaded.items():
            os.environ.setdefault(k, v)

    # Ensure API base URL is available for tests when only a host port is defined
    api_url = os.getenv("SOMABRAIN_API_URL") or os.getenv("SOMA_API_URL")
    host = os.getenv("SOMABRAIN_PUBLIC_HOST") or os.getenv("SOMABRAIN_HOST")
    port = os.getenv("SOMABRAIN_PUBLIC_PORT") or os.getenv("SOMABRAIN_HOST_PORT")
    if not api_url and port:
        # Default host to loopback when not explicitly provided
        host = host or "127.0.0.1"
        os.environ.setdefault("SOMABRAIN_API_URL", f"http://{host}:{port}")

    # Normalize container-only hostnames to localhost for host-run tests
    mem = os.getenv("SOMABRAIN_MEMORY_HTTP_ENDPOINT")
    if mem and "host.docker.internal" in mem:
        os.environ["SOMABRAIN_MEMORY_HTTP_ENDPOINT"] = mem.replace(
            "host.docker.internal", "127.0.0.1"
        )

    # Default memory endpoint to localhost:9595 for host-run if not set
    os.environ.setdefault("SOMABRAIN_MEMORY_HTTP_ENDPOINT", "http://127.0.0.1:9595")

    # Redis inside compose is addressable as somabrain_redis from containers,
    # but host-run tests must use the published host port instead.
    # If SOMABRAIN_REDIS_URL points to somabrain_redis, rewrite to localhost:REDIS_HOST_PORT.
    redis_url = os.getenv("SOMABRAIN_REDIS_URL")
    if redis_url and "somabrain_redis" in redis_url:
        host_port = os.getenv("REDIS_HOST_PORT")
        # Fall back to ports.json if REDIS_HOST_PORT is not present in env
        if not host_port:
            ports_path = root / "ports.json"
            try:
                data = json.loads(ports_path.read_text()) if ports_path.exists() else {}
                host_port = str(data.get("REDIS_HOST_PORT") or "30000")
            except Exception:
                host_port = "30000"
        os.environ["SOMABRAIN_REDIS_URL"] = f"redis://127.0.0.1:{host_port}/0"


_bootstrap_env_from_dotenv()

# Removed duplicate schema test ignore after renaming to unique filename.
# Ensure the Kafka smoke test script is ignored during pytest collection.
collect_ignore: list[str] = [
    "scripts/kafka_smoke_test.py",
]


# -------- Integration test gating (fail-fast on infra readiness) ---------
_READINESS_CACHE: dict[str, tuple[bool, str]] = {}


def _run_ci_readiness() -> tuple[bool, str]:
    """Run the repository readiness check and return (ok, output)."""
    root = Path(__file__).resolve().parents[1]
    script = root / "scripts" / "ci_readiness.py"
    if not script.exists():
        return False, f"Missing readiness script: {script}"
    try:
        proc = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
    except Exception as e:  # noqa: BLE001
        return False, f"Exception running readiness script: {type(e).__name__}: {e}"
    ok = proc.returncode == 0
    output = (proc.stdout or "") + (proc.stderr or "")
    return ok, output.strip()


@pytest.fixture(scope="session")
def integration_env_ready() -> None:
    """Ensure external services are ready before any integration test runs.

    This enforces strict-real operation: if Kafka/Redis/Postgres/OPA are not
    available, integration tests will fail fast with a clear diagnostic.
    """
    # Cache by key to avoid multiple runs in xdist or repeated sessions
    key = "default"
    if key not in _READINESS_CACHE:
        _READINESS_CACHE[key] = _run_ci_readiness()
    ok, output = _READINESS_CACHE[key]
    if not ok:
        pytest.fail(
            "Infrastructure readiness failed for integration tests.\n" + output,
            pytrace=False,
        )


def pytest_collection_modifyitems(config: pytest.Config, items: List[pytest.Item]) -> None:
    # Auto-skip performance / benchmark unless explicitly selected
    marker_expr = config.getoption("-m") or ""
    perf_selected = "performance" in marker_expr or "benchmark" in marker_expr
    for item in items:
        # Path-based heuristic marking
        p = Path(str(item.fspath))
        parts = [s.lower() for s in p.parts]
        if any(s in parts for s in ["integration", "kafka", "monitoring", "e2e", "services"]):
            item.add_marker(pytest.mark.integration)
        if "benchmarks" in parts or "stress" in parts or "benchmark" in parts:
            item.add_marker(pytest.mark.benchmark)
        if "performance" in parts:
            item.add_marker(pytest.mark.performance)

        if "performance" in item.keywords and not perf_selected:
            item.add_marker(
                pytest.mark.skip(reason="performance test skipped; use -m performance")
            )
        if "benchmark" in item.keywords and not perf_selected:
            item.add_marker(
                pytest.mark.skip(reason="benchmark test skipped; use -m benchmark")
            )
        # Inject infra readiness fixture for integration tests
        if item.get_closest_marker("integration") is not None:
            item.fixturenames.append("integration_env_ready")


# Rely on default pytest file collection. Benchmarks are path-marked and skipped by default.

# New ROAMDP test helpers
@pytest.fixture
def test_tenant_id() -> str:
    """Standard test tenant ID for all tests."""
    return "test-tenant-001"

@pytest.fixture
def default_sleep_state(test_tenant_id):
    """Default sleep state for testing."""
    from somabrain.sleep.models import TenantSleepState, SleepState
    return TenantSleepState(
        tenant_id=test_tenant_id,
        current_state=SleepState.ACTIVE,
        target_state=SleepState.ACTIVE
    )

# Performance test markers - use the existing configuration
# pytest_configure is already defined above
