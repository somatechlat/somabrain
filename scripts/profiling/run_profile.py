"""Profiling script for critical paths.

This script runs a simple load against the running SomaBrain API for a given duration
and records a cProfile report. The CI job ``profile_critical_paths`` invokes it
after starting a minimal Docker Compose deployment (only the ``somabrain_app``
service). The script is deliberately lightweight – it repeatedly hits the health
endpoint and a sample tenant endpoint, which exercises the request handling,
database access, and background worker interactions.

Usage:
    python scripts/profiling/run_profile.py --duration 30

The generated profile is written to ``profiling_report.txt`` in the repository
root.
"""

import argparse
import time
import httpx
import cProfile
import pstats
import io
import os


def _hit_endpoint(base_url: str, path: str) -> None:
    """Execute hit endpoint.

        Args:
            base_url: The base_url.
            path: The path.
        """

    try:
        resp = httpx.get(f"{base_url}{path}", timeout=5.0)
        resp.raise_for_status()
    except Exception as exc:
        # In CI we don't fail the profiling run on occasional request errors.
        print(f"Request to {path} failed: {exc}")


def main() -> None:
    """Execute main.
        """

    parser = argparse.ArgumentParser(
        description="Run a simple profiling load against the API."
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=30,
        help="Duration in seconds to run the load loop.",
    )
    from django.conf import settings as _settings

    # Use centralized Settings for environment variable access.
    parser.add_argument(
        "--base-url",
        default=_settings.api_url,
        help="Base URL of the API.",
    )
    args = parser.parse_args()

    end_time = time.time() + args.duration
    pr = cProfile.Profile()
    pr.enable()

    while time.time() < end_time:
        _hit_endpoint(args.base_url, "/health")
        _hit_endpoint(args.base_url, "/v1/tenants")
        time.sleep(1)  # modest pacing to avoid overwhelming the container

    pr.disable()
    s = io.StringIO()
    ps = pstats.Stats(pr, stream=s).sort_stats(pstats.SortKey.CUMULATIVE)
    ps.print_stats()
    report = s.getvalue()
    report_path = os.path.join(os.getcwd(), "profiling_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Profiling report written to {report_path}")


if __name__ == "__main__":
    main()