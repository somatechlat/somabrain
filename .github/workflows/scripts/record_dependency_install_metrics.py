"""Module record_dependency_install_metrics."""

from __future__ import annotations
import json
import os
import subprocess
import sys
import time
from pathlib import Path

#!/usr/bin/env python3
"""Capture dependency install metrics for SomaBrain CI.

This script wraps ``uv pip sync uv.lock`` to measure how long dependency
installation takes and how many distributions are resolved. It writes the
result to ``artifacts/bench_logs/dependency_install_metrics.json`` so Prometheus
or other internal tooling can scrape the values.

The script is idempotent and can be invoked locally to reproduce CI metrics.
When run outside CI, exports ``CI=false`` in the metric payload.
"""


REPO_ROOT = Path(__file__).resolve().parents[2]
UV_LOCK = REPO_ROOT / "uv.lock"
ARTIFACT_PATH = REPO_ROOT / "artifacts" / "bench_logs" / "dependency_install_metrics.json"


def ensure_uv_lock() -> None:
    """Execute ensure uv lock."""

    if not UV_LOCK.exists():
        raise FileNotFoundError(
            "uv.lock not found. Generate it with `uv pip install -e .[dev]` first."
        )


def run_uv_sync() -> tuple[float, subprocess.CompletedProcess[str]]:
    """Execute run uv sync."""

    cmd = ["uv", "sync", "--locked", "--all-extras"]
    start = time.perf_counter()
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    duration = time.perf_counter() - start
    if proc.returncode != 0:
        sys.stderr.write(proc.stdout)
        sys.stderr.write(proc.stderr)
        raise RuntimeError(f"`{' '.join(cmd)}` failed with exit code {proc.returncode}")
    return duration, proc


def count_locked_packages() -> int:
    """Execute count locked packages."""

    count = 0
    with UV_LOCK.open("r", encoding="utf-8") as fp:
        for line in fp:
            if line.startswith("[[package]]"):
                count += 1
    return count


def write_metrics(duration: float, package_count: int) -> None:
    """Execute write metrics.

    Args:
        duration: The duration.
        package_count: The package_count.
    """

    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "timestamp": int(time.time()),
        "ci": os.environ.get("CI", "false").lower() == "true",
        "duration_seconds": round(duration, 3),
        "package_total": package_count,
    }

    existing: list[dict] = []
    if ARTIFACT_PATH.exists():
        try:
            pass
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            existing = json.loads(ARTIFACT_PATH.read_text(encoding="utf-8"))
            if not isinstance(existing, list):
                existing = []
        except json.JSONDecodeError:
            existing = []

    existing.append(payload)
    ARTIFACT_PATH.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    """Execute main."""

    ensure_uv_lock()
    duration, _ = run_uv_sync()
    package_count = count_locked_packages()
    write_metrics(duration, package_count)
    print(
        f"Recorded dependency install metrics: duration={duration:.3f}s, packages={package_count}"
    )


if __name__ == "__main__":
    main()
