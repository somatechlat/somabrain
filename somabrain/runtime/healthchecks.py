"""Backend connectivity health checks for SomaBrain.

These helpers perform real connectivity checks to core backends used by the
runtime (Kafka and Postgres). They are designed to be fast, non-blocking, and
safe to call from the /health endpoint.

They do not depend on Prometheus exporters or scrape state; instead they verify
that a minimal control-plane operation (TCP connect and metadata/SELECT 1) is
possible. This provides a truthful readiness signal for a real server.
"""

from __future__ import annotations

from typing import Optional

from django.conf import settings


def _strip_scheme(url: str) -> str:
    """Execute strip scheme.

    Args:
        url: The url.
    """

    try:
        u = str(url or "").strip()
        if "://" in u:
            return u.split("://", 1)[1]
        return u
    except Exception:
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
        from confluent_kafka import Consumer

        c = Consumer(
            {
                "bootstrap.servers": servers,
                "group.id": "healthcheck-probe",
                "session.timeout.ms": int(max(1500, timeout_s * 1500)),
                "enable.auto.commit": False,
            }
        )
        try:
            # metadata() without args returns cluster metadata
            md = c.list_topics(timeout=timeout_s)
            ok = bool(md and md.brokers)
        finally:
            try:
                c.close()
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
        import psycopg

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
    kafka_url = getattr(settings, "KAFKA_BOOTSTRAP_SERVERS", "")
    pg_dsn = getattr(settings, "SOMABRAIN_POSTGRES_DSN", "")
    return {
        "kafka_ok": check_kafka(kafka_url),
        "postgres_ok": check_postgres(pg_dsn),
    }


# ---------------------------------------------------------------------
# SFM Integration Health Check (E3)
# Requirements: E3.1, E3.2, E3.3, E3.4, E3.5
# ---------------------------------------------------------------------
import asyncio
from dataclasses import dataclass, field
from typing import List


@dataclass
class SFMIntegrationHealth:
    """Health status including SFM components.

    Per Requirements E3.1-E3.5:
    - Reports kv_store, vector_store, graph_store status from SFM
    - Reports degraded (not failed) when any component unhealthy
    - Reports sfm_available=false when SFM completely unreachable
    - Lists specific unhealthy components
    """

    sb_healthy: bool = True
    sfm_available: bool = False
    sfm_kv_store: bool = False
    sfm_vector_store: bool = False
    sfm_graph_store: bool = False
    degraded: bool = False
    degraded_components: List[str] = field(default_factory=list)
    outbox_pending: int = 0
    error: Optional[str] = None


def check_sfm_integration_health(
    sfm_endpoint: Optional[str] = None,
    timeout_s: float = 2.0,
    tenant: str = "default",
) -> SFMIntegrationHealth:
    """Check full SB↔SFM integration health.

    Per Requirements E3.1-E3.5:
    - Calls SFM /health endpoint to get component status
    - Returns degraded (not failed) when any SFM component unhealthy
    - Times out after 2 seconds and reports unknown status
    - Lists specific unhealthy components

    Args:
        sfm_endpoint: SFM base URL (defaults to settings)
        timeout_s: Timeout in seconds (default 2.0 per E3.4)
        tenant: Tenant ID for metrics labeling

    Returns:
        SFMIntegrationHealth with component status
    """
    result = SFMIntegrationHealth()

    # Get SFM endpoint from settings if not provided
    if not sfm_endpoint:
        sfm_endpoint = getattr(settings, "SOMABRAIN_MEMORY_HTTP_ENDPOINT", None)
        if not sfm_endpoint:
            from somabrain.core.infrastructure_defs import get_memory_http_endpoint

            sfm_endpoint = get_memory_http_endpoint()

    if not sfm_endpoint:
        result.error = "SFM endpoint not configured"
        result.degraded = True
        result.degraded_components = ["sfm_endpoint"]
        return result

    # Normalize endpoint
    sfm_endpoint = sfm_endpoint.rstrip("/")
    if sfm_endpoint.endswith("/openapi.json"):
        sfm_endpoint = sfm_endpoint[: -len("/openapi.json")]

    try:
        import httpx

        # Use sync client with timeout (E3.4: 2 second timeout)
        with httpx.Client(timeout=timeout_s) as client:
            # Get API token for auth
            token = getattr(settings, "SOMABRAIN_MEMORY_HTTP_TOKEN", None) or getattr(
                settings, "api_token", None
            )
            headers = {}
            if token:
                headers["Authorization"] = f"Bearer {token}"
            headers["X-Soma-Tenant"] = tenant

            # Call SFM health endpoint
            response = client.get(f"{sfm_endpoint}/health", headers=headers)

            if response.status_code == 200:
                data = response.json()
                result.sfm_available = True

                # Extract component status (E3.1)
                result.sfm_kv_store = data.get("kv_store", False)
                result.sfm_vector_store = data.get("vector_store", False)
                result.sfm_graph_store = data.get("graph_store", False)

                # Determine degraded status (E3.2, E3.5)
                degraded_components = []
                if not result.sfm_kv_store:
                    degraded_components.append("kv_store")
                if not result.sfm_vector_store:
                    degraded_components.append("vector_store")
                if not result.sfm_graph_store:
                    degraded_components.append("graph_store")

                result.degraded_components = degraded_components
                result.degraded = len(degraded_components) > 0
            else:
                # SFM returned error - degraded mode (E3.2)
                result.sfm_available = False
                result.degraded = True
                result.degraded_components = ["sfm_api"]
                result.error = f"SFM returned status {response.status_code}"

    except httpx.TimeoutException:
        # Timeout - report unknown status (E3.4)
        result.sfm_available = False
        result.degraded = True
        result.degraded_components = ["sfm_timeout"]
        result.error = f"SFM health check timed out after {timeout_s}s"
    except Exception as exc:
        # SFM unreachable - degraded with sfm_available=false (E3.3)
        result.sfm_available = False
        result.degraded = True
        result.degraded_components = ["sfm_unreachable"]
        result.error = str(exc)

    return result


async def check_sfm_integration_health_async(
    sfm_endpoint: Optional[str] = None,
    timeout_s: float = 2.0,
    tenant: str = "default",
) -> SFMIntegrationHealth:
    """Async version of check_sfm_integration_health.

    Same behavior as sync version but uses async HTTP client.
    """
    result = SFMIntegrationHealth()

    # Get SFM endpoint from settings if not provided
    if not sfm_endpoint:
        sfm_endpoint = getattr(settings, "SOMABRAIN_MEMORY_HTTP_ENDPOINT", None)
        if not sfm_endpoint:
            from somabrain.core.infrastructure_defs import get_memory_http_endpoint

            sfm_endpoint = get_memory_http_endpoint()

    if not sfm_endpoint:
        result.error = "SFM endpoint not configured"
        result.degraded = True
        result.degraded_components = ["sfm_endpoint"]
        return result

    # Normalize endpoint
    sfm_endpoint = sfm_endpoint.rstrip("/")
    if sfm_endpoint.endswith("/openapi.json"):
        sfm_endpoint = sfm_endpoint[: -len("/openapi.json")]

    try:
        import httpx

        # Use async client with timeout (E3.4: 2 second timeout)
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            # Get API token for auth
            token = getattr(settings, "SOMABRAIN_MEMORY_HTTP_TOKEN", None) or getattr(
                settings, "api_token", None
            )
            headers = {}
            if token:
                headers["Authorization"] = f"Bearer {token}"
            headers["X-Soma-Tenant"] = tenant

            # Call SFM health endpoint
            response = await client.get(f"{sfm_endpoint}/health", headers=headers)

            if response.status_code == 200:
                data = response.json()
                result.sfm_available = True

                # Extract component status (E3.1)
                result.sfm_kv_store = data.get("kv_store", False)
                result.sfm_vector_store = data.get("vector_store", False)
                result.sfm_graph_store = data.get("graph_store", False)

                # Determine degraded status (E3.2, E3.5)
                degraded_components = []
                if not result.sfm_kv_store:
                    degraded_components.append("kv_store")
                if not result.sfm_vector_store:
                    degraded_components.append("vector_store")
                if not result.sfm_graph_store:
                    degraded_components.append("graph_store")

                result.degraded_components = degraded_components
                result.degraded = len(degraded_components) > 0
            else:
                result.sfm_available = False
                result.degraded = True
                result.degraded_components = ["sfm_api"]
                result.error = f"SFM returned status {response.status_code}"

    except asyncio.TimeoutError:
        result.sfm_available = False
        result.degraded = True
        result.degraded_components = ["sfm_timeout"]
        result.error = f"SFM health check timed out after {timeout_s}s"
    except Exception as exc:
        result.sfm_available = False
        result.degraded = True
        result.degraded_components = ["sfm_unreachable"]
        result.error = str(exc)

    return result
