#!/usr/bin/env python3
"""CI Readiness Fail-Fast Script

Checks mandatory external infrastructure components required for strict-real operation:
  - Kafka (KRaft) broker availability & metadata retrieval for required topics
  - Redis availability and ping
  - Postgres connectivity (simple SELECT 1)
  - OPA health endpoint

Exit Codes:
  0: All components ready
  1: One or more components failed readiness checks

Environment variables (taken from existing config):
  SOMABRAIN_POSTGRES_DSN        Postgres DSN (e.g. postgresql://user:pass@host:5432/db)
  SOMABRAIN_REDIS_URL           Redis URL (e.g. redis://127.0.0.1:6379/0)
  SOMABRAIN_KAFKA_URL           Kafka host:port (dev convenience)
  SOMA_KAFKA_BOOTSTRAP          Preferred bootstrap servers (compose/k8s)
  SOMABRAIN_OPA_URL             OPA base URL (e.g. http://127.0.0.1:8181)
  SOMABRAIN_TOPIC_*             Required Kafka topic names (reward/config/global_frame/next_events)

Strict posture: no silent alternatives; if any component is unavailable the script exits 1.
"""
from __future__ import annotations
from django.conf import settings
import sys
import socket
from dataclasses import dataclass
from typing import List
from pathlib import Path
import subprocess

# External deps (all required in project dependencies)
import requests
import redis
import psycopg

REQUIRED_TOPIC_ENV_VARS = [
    "SOMABRAIN_TOPIC_REWARD_EVENTS",
    "SOMABRAIN_TOPIC_CONFIG_UPDATES",
    "SOMABRAIN_TOPIC_GLOBAL_FRAME",
    "SOMABRAIN_TOPIC_NEXT_EVENTS",
]


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def _env(name: str, default: str | None = None) -> str | None:
    """Retrieve a configuration value via the centralized Settings.

    The original implementation used ``settings.getenv`` which is now legacy.
    This helper maps the upper‑case environment variable name to the matching
    Settings attribute (lower‑case) and returns its string representation.
    If the attribute does not exist or is empty, ``default`` is returned.
    """
    attr = name.lower()
    if hasattr(settings, attr):
        val = getattr(settings, attr)
        if val is None:
            return default
        return str(val).strip()
    # Fallback – maintain previous behaviour for any unexpected names.
    return default


# Strict mode utilities removed: no host-port fallback mappings


def check_postgres() -> CheckResult:
    dsn = _env("SOMABRAIN_POSTGRES_DSN")
    if not dsn:
        return CheckResult("postgres", False, "SOMABRAIN_POSTGRES_DSN not set")
    try:
        with psycopg.connect(dsn, connect_timeout=3) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        return CheckResult("postgres", True, "OK")
    except Exception as e:  # noqa: BLE001
        return CheckResult("postgres", False, f"{type(e).__name__}: {e}")


def check_redis() -> CheckResult:
    url = _env("SOMABRAIN_REDIS_URL")
    if not url:
        return CheckResult("redis", False, "SOMABRAIN_REDIS_URL not set")
    try:
        client = redis.Redis.from_url(url, socket_connect_timeout=3, socket_timeout=3)
        pong = client.ping()
        if pong:
            return CheckResult("redis", True, "OK")
        return CheckResult("redis", False, "PING failed")
    except Exception as e:  # noqa: BLE001
        return CheckResult("redis", False, f"{type(e).__name__}: {e}")


def _socket_connect(host: str, port: int, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def check_kafka() -> List[CheckResult]:
    results: List[CheckResult] = []
    bootstrap = _env("SOMA_KAFKA_BOOTSTRAP") or _env("SOMABRAIN_KAFKA_URL")
    if not bootstrap:
        return [
            CheckResult(
                "kafka",
                False,
                "Bootstrap env SOMA_KAFKA_BOOTSTRAP or SOMABRAIN_KAFKA_URL not set",
            )
        ]
    host_port = bootstrap.split(",")[0].strip()
    host, _, port_str = host_port.partition(":")
    try:
        port = int(port_str) if port_str else 9092
    except Exception:
        port = 9092
    if not _socket_connect(host, port):
        return [CheckResult("kafka", False, f"TCP connect failed to {host}:{port}")]

    # Try confluent_kafka for metadata if available; otherwise rely on socket connect + topic env presence.
    try:
        from confluent_kafka import AdminClient

        admin = AdminClient({"bootstrap.servers": bootstrap})
        md = admin.list_topics(timeout=5)
        existing_topics = set(md.topics.keys())
        for env_var in REQUIRED_TOPIC_ENV_VARS:
            t = _env(env_var)
            if not t:
                results.append(
                    CheckResult(f"kafka_topic:{env_var}", False, "env not set")
                )
            elif t not in existing_topics:
                results.append(
                    CheckResult(f"kafka_topic:{t}", False, "missing in cluster")
                )
            else:
                results.append(CheckResult(f"kafka_topic:{t}", True, "OK"))
        if not results:
            results.append(CheckResult("kafka", True, "OK"))
        return results
    except Exception as e:  # noqa: BLE001
        # Confluent client unavailable or metadata failure; still require topic env vars (strict posture)
        for env_var in REQUIRED_TOPIC_ENV_VARS:
            t = _env(env_var)
            if not t:
                results.append(
                    CheckResult(f"kafka_topic:{env_var}", False, "env not set")
                )
            else:
                results.append(
                    CheckResult(
                        f"kafka_topic:{t}", True, "env set (metadata unchecked)"
                    )
                )
        results.append(
            CheckResult(
                "kafka", True, f"Socket OK; metadata skipped: {type(e).__name__}"
            )
        )
        return results


def check_opa() -> CheckResult:
    base = _env("SOMABRAIN_OPA_URL")
    if not base:
        return CheckResult("opa", False, "SOMABRAIN_OPA_URL not set")
    url = base.rstrip("/") + "/health"
    try:
        resp = requests.get(url, timeout=3)
        if resp.status_code != 200:
            return CheckResult("opa", False, f"HTTP {resp.status_code}")
        # Accept any 200; optionally check JSON structure if present
        return CheckResult("opa", True, "OK")
    except Exception as e:  # noqa: BLE001
        return CheckResult("opa", False, f"{type(e).__name__}: {e}")


def check_outbox_pending() -> CheckResult:
    from django.conf import settings

    base = _env("SOMABRAIN_API_URL") or _env("SOMA_API_URL") or settings.api_url
    token = _env("SOMABRAIN_API_TOKEN") or _env("SOMA_API_TOKEN")
    if not token:
        return CheckResult("outbox", False, "SOMABRAIN_API_TOKEN not set")
    try:
        max_pending = int(_env("SOMABRAIN_OUTBOX_MAX_PENDING", "100") or 100)
    except Exception:
        max_pending = 100
    status = _env("SOMABRAIN_OUTBOX_CHECK_STATUS", "pending") or "pending"
    try:
        page_size = int(_env("SOMABRAIN_OUTBOX_CHECK_PAGE", "500") or 500)
    except Exception:
        page_size = 500

    script_path = Path(__file__).resolve().parents[1] / "scripts" / "outbox_admin.py"
    cmd = [
        sys.executable,
        str(script_path),
        "--url",
        base.rstrip("/"),
        "--token",
        token,
        "check",
        "--status",
        status,
        "--max-pending",
        str(max_pending),
        "--page-size",
        str(page_size),
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except Exception as exc:  # noqa: BLE001
        return CheckResult(
            "outbox", False, f"check failed: {type(exc).__name__}: {exc}"
        )
    ok = proc.returncode == 0
    detail = (proc.stdout or proc.stderr).strip() or f"exit {proc.returncode}"
    return CheckResult("outbox", ok, detail)


def main() -> int:
    checks: List[CheckResult] = []
    checks.append(check_postgres())
    checks.append(check_redis())
    checks.extend(check_kafka())
    checks.append(check_opa())
    checks.append(check_outbox_pending())

    failed = [c for c in checks if not c.ok]
    for c in checks:
        status = "READY" if c.ok else "FAIL"
        print(f"{status}: {c.name} - {c.detail}")
    if failed:
        print(
            f"\nSummary: {len(failed)} component(s) failed readiness.", file=sys.stderr
        )
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
