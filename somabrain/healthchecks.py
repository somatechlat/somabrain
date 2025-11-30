from __future__ import annotations
from typing import Optional
from common.config.settings import settings
from common.logging import logger
from confluent_kafka import Consumer  # type: ignore
import psycopg  # type: ignore

"""Backend connectivity health checks for SomaBrain.

These helpers perform real connectivity checks to core backends used by the
runtime (Kafka and Postgres). They are designed to be fast, non-blocking, and
safe to call from the /health endpoint.

They do not depend on Prometheus exporters or scrape state; instead they verify
that a minimal control-plane operation (TCP connect and metadata/SELECT 1) is
possible. This provides a truthful readiness signal for a real server.
"""





def _strip_scheme(url: str) -> str:
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        u = str(url or "").strip()
        if "://" in u:
            return u.split("://", 1)[1]
        return u
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        return str(url or "").strip()


def check_kafka(bootstrap: Optional[str], timeout_s: float = 1.0) -> bool:
    """Return True if we can connect to the Kafka broker and fetch metadata (confluent-kafka).

    Uses a metadata-only Consumer subscribe to no topics and polls for cluster metadata.
    Strict mode: kafka-python is not permitted.
    """
    if not bootstrap:
        return False
    servers = _strip_scheme(bootstrap)
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise

        c = Consumer(
            {
                "bootstrap.servers": servers,
                "group.id": "healthcheck-probe",
                "session.timeout.ms": int(max(1500, timeout_s * 1500)),
                "enable.auto.commit": False,
            }
        )
        try:
            pass
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            # metadata() without args returns cluster metadata
            md = c.list_topics(timeout=timeout_s)
            ok = bool(md and md.brokers)
        finally:
            try:
                pass
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
                c.close()
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
        return ok
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        return False


def check_postgres(dsn: Optional[str], timeout_s: float = 1.0) -> bool:
    """Return True if we can connect to Postgres and SELECT 1.

    Uses psycopg3 if available. Falls back to False on import or connect errors.
    """
    if not dsn:
        return False
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise

        # psycopg.connect supports connect_timeout as kwarg (seconds)
        conn = psycopg.connect(dsn, connect_timeout=max(1, int(timeout_s)))
        try:
            pass
        except Exception as exc:
            logger.exception("Exception caught: %s", exc)
            raise
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                row = cur.fetchone()
                return bool(row and row[0] == 1)
        finally:
            try:
                pass
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
                conn.close()
            except Exception as exc:
                logger.exception("Exception caught: %s", exc)
                raise
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        return False


def check_from_env() -> dict[str, bool]:
    """Convenience: check Kafka/Postgres based on common SOMABRAIN_* envs."""
    kafka_url = getattr(settings, "kafka_bootstrap_servers", "")
    pg_dsn = getattr(settings, "postgres_dsn", "")
    return {
        "kafka_ok": check_kafka(kafka_url),
        "postgres_ok": check_postgres(pg_dsn),
    }
