"""Pytest configuration for environment bootstrapping.

This file loads environment variables from `.env` (if present) so tests
automatically discover the correct host port mappings for services brought up by
scripts/dev_up.sh. We avoid relying on long shell commands or passing params via
the console; tests derive their runtime config from the repo's env files.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict
import json


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


# Eagerly load on import so all tests see a consistent environment
_bootstrap_env_from_dotenv()
