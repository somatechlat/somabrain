from __future__ import annotations

import os
import socket
from typing import Optional, Tuple


def _strip(url: Optional[str]) -> str:
    u = (url or "").strip()
    return u.split("://", 1)[1] if "://" in u else u


def check_kafka(bootstrap: Optional[str], timeout_s: float = 2.0) -> bool:
    bs = _strip(bootstrap)
    if not bs:
        return False
    try:
        from confluent_kafka import Consumer  # type: ignore

        c = Consumer(
            {
                "bootstrap.servers": bs,
                "group.id": "infra-check",
                "enable.auto.commit": False,
                "session.timeout.ms": int(max(1500, timeout_s * 1500)),
            }
        )
        try:
            md = c.list_topics(timeout=timeout_s)
            return bool(md and md.brokers)
        finally:
            try:
                c.close()
            except Exception:
                pass
    except Exception:
        return False


def check_redis(redis_url: Optional[str], timeout_s: float = 2.0) -> bool:
    url = (redis_url or os.getenv("SOMABRAIN_REDIS_URL") or "").strip()
    if not url:
        return False
    try:
        import redis  # type: ignore

        r = redis.from_url(url, socket_timeout=timeout_s)
        return bool(r.ping())
    except Exception:
        return False


def check_postgres(dsn: Optional[str], timeout_s: float = 2.0) -> bool:
    dsn = (dsn or os.getenv("SOMABRAIN_POSTGRES_DSN") or "").strip()
    if not dsn:
        return False
    try:
        import psycopg  # type: ignore

        conn = psycopg.connect(dsn, connect_timeout=max(1, int(timeout_s)))
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                row = cur.fetchone()
                return bool(row and row[0] == 1)
        finally:
            try:
                conn.close()
            except Exception:
                pass
    except Exception:
        return False


def check_opa(opa_url: Optional[str], timeout_s: float = 2.0) -> bool:
    url = (opa_url or os.getenv("SOMABRAIN_OPA_URL") or "").strip().rstrip("/")
    if not url:
        # Treat missing OPA as not configured rather than down
        return True
    try:
        import requests  # type: ignore

        # Try a cheap GET on /health (if available), else root
        for path in ("/health", "/v1/policies"):
            try:
                resp = requests.get(url + path, timeout=timeout_s)
                if resp.status_code < 500:
                    return True
            except Exception:
                continue
        return False
    except Exception:
        return False


def assert_ready(
    *,
    require_kafka: bool = True,
    require_redis: bool = True,
    require_postgres: bool = True,
    require_opa: bool = False,
    timeout_s: float = 2.0,
) -> None:
    """Fail fast if required backends are not ready.

    Requirements can be tuned via function args. Environment also supports
    global gate: set SOMABRAIN_REQUIRE_INFRA=0 to bypass (not recommended).
    """
    if os.getenv("SOMABRAIN_REQUIRE_INFRA", "1").strip().lower() in {
        "0",
        "false",
        "no",
        "off",
    }:
        return
    errors = []
    if require_kafka:
        if not check_kafka(os.getenv("SOMABRAIN_KAFKA_URL"), timeout_s=timeout_s):
            errors.append("Kafka")
    if require_redis:
        if not check_redis(os.getenv("SOMABRAIN_REDIS_URL"), timeout_s=timeout_s):
            errors.append("Redis")
    if require_postgres:
        if not check_postgres(os.getenv("SOMABRAIN_POSTGRES_DSN"), timeout_s=timeout_s):
            errors.append("Postgres")
    if require_opa:
        if not check_opa(os.getenv("SOMABRAIN_OPA_URL"), timeout_s=timeout_s):
            errors.append("OPA")
    if errors:
        raise RuntimeError(f"Infra not ready: {', '.join(errors)}")


__all__ = [
    "check_kafka",
    "check_redis",
    "check_postgres",
    "check_opa",
    "assert_ready",
]
