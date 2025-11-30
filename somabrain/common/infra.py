from __future__ import annotations

from typing import Optional
from common.config.settings import settings


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
    """Check Redis connectivity using the centralized ``Settings``.

    Preference is given to the explicit ``redis_url`` argument; if omitted we
    fall back to ``settings.redis_url`` which is the single source of truth for
    the Redis endpoint across the codebase.
    """
    # Import lazily to avoid circular imports at module load time.
    # Directly use the imported ``settings`` singleton.
    url = (redis_url or getattr(settings, "redis_url", None) or "").strip()
    if not url:
        return False
    try:
        import redis  # type: ignore

        r = redis.from_url(url, socket_timeout=timeout_s)
        return bool(r.ping())
    except Exception:
        return False


def check_postgres(dsn: Optional[str], timeout_s: float = 2.0) -> bool:
    """Validate Postgres connectivity using the centralized ``Settings``.

    The function prefers an explicit ``dsn`` argument; if ``None`` it reads the
    value from ``settings.postgres_dsn`` which is the authoritative source for the
    database connection string.
    """
    # Directly use the imported ``settings`` singleton.
    dsn = (dsn or getattr(settings, "postgres_dsn", None) or "").strip()
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
    """Check OPA health using the centralized configuration.

    If no URL is configured we treat OPA as optional (return ``True``) to keep
    the original semantics.
    """
    # Directly use the imported ``settings`` singleton.
    url = (opa_url or getattr(settings, "opa_url", None) or "").strip().rstrip("/")
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
    if settings.require_infra.strip().lower() in {
        "0",
        "false",
        "no",
        "off",
    }:
        return
    errors = []
    # Use centralized settings where possible for consistency.
    if require_kafka:
        if not check_kafka(
            getattr(settings, "kafka_bootstrap_servers", None),
            timeout_s=timeout_s,
        ):
            errors.append("Kafka")
    if require_redis:
        if not check_redis(
            getattr(settings, "redis_url", None),
            timeout_s=timeout_s,
        ):
            errors.append("Redis")
    if require_postgres:
        if not check_postgres(
            getattr(settings, "postgres_dsn", None),
            timeout_s=timeout_s,
        ):
            errors.append("Postgres")
    if require_opa:
        if not check_opa(
            getattr(settings, "opa_url", None),
            timeout_s=timeout_s,
        ):
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
