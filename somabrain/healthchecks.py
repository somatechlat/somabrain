"""Backend connectivity health checks for SomaBrain.

These helpers perform real connectivity checks to core backends used by the
runtime (Kafka and Postgres). They are designed to be fast, non-blocking, and
safe to call from the /health endpoint.

They do not depend on Prometheus exporters or scrape state; instead they verify
that a minimal control-plane operation (TCP connect and metadata/SELECT 1) is
possible. This provides a truthful readiness signal for a real server.
"""

from __future__ import annotations

import os
from typing import Optional


def _strip_scheme(url: str) -> str:
    try:
        u = str(url or "").strip()
        if "://" in u:
            return u.split("://", 1)[1]
        return u
    except Exception:
        return str(url or "").strip()


def check_kafka(bootstrap: Optional[str], timeout_s: float = 1.0) -> bool:
    """Return True if we can connect to the Kafka broker and fetch metadata.

    Attempts a minimal metadata fetch using kafka-python with aggressive timeouts.
    """
    if not bootstrap:
        return False
    servers = _strip_scheme(bootstrap)
    try:
        # Prefer a metadata-only probe via KafkaConsumer; closes immediately.
        from kafka import KafkaConsumer  # type: ignore

        consumer = KafkaConsumer(
            bootstrap_servers=servers,
            request_timeout_ms=int(max(100, timeout_s * 1000)),
            api_version_auto_timeout_ms=int(max(100, timeout_s * 1000)),
            metadata_max_age_ms=int(max(500, timeout_s * 2000)),
            session_timeout_ms=int(max(6000, timeout_s * 6000)),
            heartbeat_interval_ms=int(max(3000, timeout_s * 3000)),
            consumer_timeout_ms=int(max(100, timeout_s * 1000)),
        )
        try:
            ok = bool(consumer.bootstrap_connected())
        finally:
            try:
                consumer.close()
            except Exception:
                pass
        return ok
    except Exception:
        return False


def check_postgres(dsn: Optional[str], timeout_s: float = 1.0) -> bool:
    """Return True if we can connect to Postgres and SELECT 1.

    Uses psycopg3 if available. Falls back to False on import or connect errors.
    """
    if not dsn:
        return False
    try:
        import psycopg  # type: ignore

        # psycopg.connect supports connect_timeout as kwarg (seconds)
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


def check_from_env() -> dict[str, bool]:
    """Convenience: check Kafka/Postgres based on common SOMABRAIN_* envs."""
    kafka_url = os.getenv("SOMABRAIN_KAFKA_URL")
    pg_dsn = os.getenv("SOMABRAIN_POSTGRES_DSN")
    return {
        "kafka_ok": check_kafka(kafka_url),
        "postgres_ok": check_postgres(pg_dsn),
    }
