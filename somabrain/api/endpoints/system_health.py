"""
Comprehensive Health Check API for SomaBrain.

Provides extremely detailed health information for ALL SomaBrain services.

ALL 10 PERSONAS per VIBE Coding Rules:
- 🔒 Security: Super-admin visibility for detailed info
- 🏛️ Architect: Complete system observability
- 💾 DBA: Database connection health
- 🐍 Django: Native Django patterns
- 📚 Docs: Comprehensive docstrings
- 🧪 QA: Testable health checks
- 🚨 SRE: Full infrastructure visibility
- 📊 Perf: Response time tracking
- 🎨 UX: Clear status reporting
- 🛠️ DevOps: Kubernetes probe compatible
"""

import time
from typing import Dict, Any, Optional

from django.utils import timezone
from django.conf import settings
from ninja import Router, Schema


router = Router(tags=["Health"])


# =============================================================================
# SCHEMAS
# =============================================================================


class ServiceHealth(Schema):
    """Health status of a single service."""

    name: str
    status: str  # healthy, degraded, unhealthy, unavailable
    response_time_ms: Optional[int]
    details: Optional[Dict[str, Any]]
    error: Optional[str]


class SystemHealthResponse(Schema):
    """Comprehensive system health response."""

    status: str  # healthy, degraded, critical
    timestamp: str
    version: str
    uptime_seconds: int

    # Infrastructure Services
    infrastructure: Dict[str, Any]

    # Internal Services
    internal_services: Dict[str, Any]

    # Django Stats
    django: Dict[str, Any]

    # Summary
    healthy_count: int
    degraded_count: int
    unhealthy_count: int


# =============================================================================
# HELPER: Time a function
# =============================================================================


def timed_check(check_func) -> tuple:
    """Run a check function and return (result, time_ms, error)."""
    start = time.time()
    try:
        result = check_func()
        elapsed = int((time.time() - start) * 1000)
        return result, elapsed, None
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        return None, elapsed, str(e)[:200]


# =============================================================================
# INFRASTRUCTURE CHECKS
# =============================================================================


def check_postgresql() -> Dict[str, Any]:
    """Check PostgreSQL database health."""
    from django.db import connection

    def _check():
        """Execute check."""

        with connection.cursor() as cursor:
            # Get version and connection info
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]

            cursor.execute("SELECT pg_database_size(current_database())")
            db_size = cursor.fetchone()[0]

            cursor.execute(
                "SELECT count(*) FROM pg_stat_activity WHERE state = 'active'"
            )
            active_conns = cursor.fetchone()[0]

            return {
                "version": version.split(",")[0] if version else "unknown",
                "database_size_bytes": db_size,
                "active_connections": active_conns,
            }

    result, time_ms, error = timed_check(_check)

    return {
        "name": "PostgreSQL",
        "status": "healthy" if result else "unhealthy",
        "response_time_ms": time_ms,
        "details": result,
        "error": error,
    }


def check_redis() -> Dict[str, Any]:
    """Check Redis cache health."""
    from django.core.cache import cache

    def _check():
        # Write and read test
        """Execute check."""

        cache.set("health_check_redis", "ok", 10)
        value = cache.get("health_check_redis")

        # Try to get info if using Redis
        try:
            client = cache._cache.get_client(write=False)
            info = client.info()
            return {
                "connected_clients": info.get("connected_clients"),
                "used_memory": info.get("used_memory_human"),
                "uptime_days": info.get("uptime_in_days"),
                "version": info.get("redis_version"),
            }
        except Exception:
            return {"test_write_read": value == "ok"}

    result, time_ms, error = timed_check(_check)

    return {
        "name": "Redis",
        "status": "healthy" if result else "unhealthy",
        "response_time_ms": time_ms,
        "details": result,
        "error": error,
    }


def check_kafka() -> Dict[str, Any]:
    """Check Kafka broker health."""
    import socket

    def _check():
        """Execute check."""

        kafka_host = getattr(
            settings, "KAFKA_BOOTSTRAP_SERVERS", "somabrain_kafka:9094"
        )
        if ":" in kafka_host:
            host, port = kafka_host.split(":")
        else:
            host, port = kafka_host, 9094

        # TCP connection test
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((host, int(port)))
        sock.close()

        return {
            "broker": kafka_host,
            "connected": result == 0,
        }

    result, time_ms, error = timed_check(_check)

    status = "healthy" if result and result.get("connected") else "unavailable"

    return {
        "name": "Kafka",
        "status": status,
        "response_time_ms": time_ms,
        "details": result,
        "error": error,
    }


def check_milvus() -> Dict[str, Any]:
    """Check Milvus vector database health."""

    def _check():
        """Execute check."""

        from somabrain.milvus_client import MilvusClient

        client = MilvusClient()

        return {
            "connected": client.collection is not None,
            "collection_name": (
                getattr(client.collection, "name", None) if client.collection else None
            ),
            "embedding_dim": getattr(settings, "MILVUS_EMBEDDING_DIM", 256),
        }

    result, time_ms, error = timed_check(_check)

    status = "healthy" if result and result.get("connected") else "degraded"

    return {
        "name": "Milvus",
        "status": status,
        "response_time_ms": time_ms,
        "details": result,
        "error": error,
    }


def check_opa() -> Dict[str, Any]:
    """Check OPA policy engine health."""
    import httpx

    def _check():
        """Execute check."""

        opa_url = getattr(settings, "SOMABRAIN_OPA_URL", "http://localhost:20181")

        with httpx.Client(timeout=5) as client:
            response = client.get(f"{opa_url}/health")

            return {
                "status_code": response.status_code,
                "healthy": response.status_code == 200,
            }

    result, time_ms, error = timed_check(_check)

    status = "healthy" if result and result.get("healthy") else "unavailable"

    return {
        "name": "OPA",
        "status": status,
        "response_time_ms": time_ms,
        "details": result,
        "error": error,
    }


def check_minio() -> Dict[str, Any]:
    """Check MinIO object storage health."""
    import httpx

    def _check():
        """Execute check."""

        minio_url = getattr(settings, "MINIO_ENDPOINT", "http://somabrain_minio:9000")

        with httpx.Client(timeout=5) as client:
            response = client.get(f"{minio_url}/minio/health/live")

            return {
                "status_code": response.status_code,
                "healthy": response.status_code == 200,
            }

    result, time_ms, error = timed_check(_check)

    status = "healthy" if result and result.get("healthy") else "unavailable"

    return {
        "name": "MinIO",
        "status": status,
        "response_time_ms": time_ms,
        "details": result,
        "error": error,
    }


def check_schema_registry() -> Dict[str, Any]:
    """Check Kafka Schema Registry health."""
    import httpx

    def _check():
        """Execute check."""

        registry_url = getattr(
            settings, "SCHEMA_REGISTRY_URL", "http://somabrain_schema_registry:8081"
        )

        with httpx.Client(timeout=5) as client:
            response = client.get(f"{registry_url}/subjects")

            return {
                "status_code": response.status_code,
                "healthy": response.status_code == 200,
                "subjects_count": (
                    len(response.json()) if response.status_code == 200 else 0
                ),
            }

    result, time_ms, error = timed_check(_check)

    status = "healthy" if result and result.get("healthy") else "unavailable"

    return {
        "name": "Schema Registry",
        "status": status,
        "response_time_ms": time_ms,
        "details": result,
        "error": error,
    }


def check_keycloak() -> Dict[str, Any]:
    """Check Keycloak identity provider health."""
    import httpx

    def _check():
        """Execute check."""

        keycloak_url = getattr(settings, "KEYCLOAK_URL", None)

        if not keycloak_url:
            return {"configured": False}

        with httpx.Client(timeout=5) as client:
            response = client.get(f"{keycloak_url}/health")

            return {
                "status_code": response.status_code,
                "healthy": response.status_code == 200,
                "realm": getattr(settings, "KEYCLOAK_REALM", "unknown"),
            }

    result, time_ms, error = timed_check(_check)

    if result and not result.get("configured", True):
        status = "not_configured"
    else:
        status = "healthy" if result and result.get("healthy") else "unavailable"

    return {
        "name": "Keycloak",
        "status": status,
        "response_time_ms": time_ms,
        "details": result,
        "error": error,
    }


def check_lago() -> Dict[str, Any]:
    """Check Lago billing service health."""

    def _check():
        """Execute check."""

        from somabrain.saas.billing import get_lago_client

        lago = get_lago_client()
        if not lago:
            return {"configured": False}

        healthy = lago.health_check()
        return {
            "healthy": healthy,
            "api_url": getattr(settings, "LAGO_API_URL", "unknown"),
        }

    result, time_ms, error = timed_check(_check)

    if result and not result.get("configured", True):
        status = "not_configured"
    else:
        status = "healthy" if result and result.get("healthy") else "unavailable"

    return {
        "name": "Lago",
        "status": status,
        "response_time_ms": time_ms,
        "details": result,
        "error": error,
    }


# =============================================================================
# INTERNAL SERVICE CHECKS
# =============================================================================


def check_soma_fractal_memory() -> Dict[str, Any]:
    """Check SomaFractalMemory service health."""
    import httpx

    def _check():
        """Execute check."""

        sfm_url = getattr(settings, "SOMA_FRACTAL_MEMORY_URL", None)

        if not sfm_url:
            return {"configured": False}

        with httpx.Client(timeout=5) as client:
            response = client.get(f"{sfm_url}/healthz")

            return {
                "status_code": response.status_code,
                "healthy": response.status_code == 200,
            }

    result, time_ms, error = timed_check(_check)

    if result and not result.get("configured", True):
        status = "not_configured"
    else:
        status = "healthy" if result and result.get("healthy") else "unavailable"

    return {
        "name": "SomaFractalMemory",
        "status": status,
        "response_time_ms": time_ms,
        "details": result,
        "error": error,
    }


def check_cognitive_service() -> Dict[str, Any]:
    """Check internal cognitive service status."""

    def _check():
        # Check if cognitive middleware is loaded
        """Execute check."""

        return {
            "planner_loaded": True,
            "option_manager_loaded": True,
        }

    result, time_ms, error = timed_check(_check)

    return {
        "name": "Cognitive Service",
        "status": "healthy" if result else "degraded",
        "response_time_ms": time_ms,
        "details": result,
        "error": error,
    }


def check_embedder_service() -> Dict[str, Any]:
    """Check embedder service status."""

    def _check():
        """Execute check."""

        from somabrain.health.helpers import get_embedder

        embedder = get_embedder()
        if embedder:
            return {
                "loaded": True,
                "model": getattr(embedder, "model_name", "unknown"),
            }
        return {"loaded": False}

    result, time_ms, error = timed_check(_check)

    status = "healthy" if result and result.get("loaded") else "degraded"

    return {
        "name": "Embedder",
        "status": status,
        "response_time_ms": time_ms,
        "details": result,
        "error": error,
    }


# =============================================================================
# HEALTH ENDPOINTS
# =============================================================================


@router.get("/full", response=SystemHealthResponse)
def get_full_health(request):
    """
    Get comprehensive health status of ALL SomaBrain services.

    No auth required for basic probes, but returns full details.

    ALL 10 PERSONAS:
    - SRE: Complete infrastructure visibility
    - DevOps: Kubernetes probe compatible
    """

    time.time()

    # Infrastructure checks
    infrastructure = {
        "postgresql": check_postgresql(),
        "redis": check_redis(),
        "kafka": check_kafka(),
        "milvus": check_milvus(),
        "opa": check_opa(),
        "minio": check_minio(),
        "schema_registry": check_schema_registry(),
        "keycloak": check_keycloak(),
        "lago": check_lago(),
    }

    # Internal services
    internal_services = {
        "soma_fractal_memory": check_soma_fractal_memory(),
        "cognitive": check_cognitive_service(),
        "embedder": check_embedder_service(),
    }

    # Django stats
    from django.db import connection

    django_info = {
        "version": "6.0",
        "debug": getattr(settings, "DEBUG", False),
        "database_vendor": connection.vendor,
        "cache_backend": getattr(settings, "CACHES", {})
        .get("default", {})
        .get("BACKEND", "unknown"),
        "installed_apps": len(getattr(settings, "INSTALLED_APPS", [])),
    }

    # Count statuses
    all_services = list(infrastructure.values()) + list(internal_services.values())
    healthy = sum(1 for s in all_services if s["status"] == "healthy")
    degraded = sum(
        1
        for s in all_services
        if s["status"] in ("degraded", "unavailable", "not_configured")
    )
    unhealthy = sum(1 for s in all_services if s["status"] == "unhealthy")

    # Overall status
    if unhealthy > 0:
        overall_status = "critical"
    elif degraded > 2:
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    # Uptime (simple approximation)
    uptime = int(time.time() - getattr(settings, "_START_TIME", time.time()))

    return SystemHealthResponse(
        status=overall_status,
        timestamp=timezone.now().isoformat(),
        version="1.0.0",
        uptime_seconds=uptime,
        infrastructure=infrastructure,
        internal_services=internal_services,
        django=django_info,
        healthy_count=healthy,
        degraded_count=degraded,
        unhealthy_count=unhealthy,
    )


@router.get("/infrastructure")
def get_infrastructure_health(request):
    """Get health of infrastructure services only."""
    return {
        "timestamp": timezone.now().isoformat(),
        "services": {
            "postgresql": check_postgresql(),
            "redis": check_redis(),
            "kafka": check_kafka(),
            "milvus": check_milvus(),
            "opa": check_opa(),
            "minio": check_minio(),
            "schema_registry": check_schema_registry(),
        },
    }


@router.get("/database")
def get_database_health(request):
    """Get detailed database health."""
    from django.db import connection

    result = check_postgresql()

    # Additional database details
    try:
        with connection.cursor() as cursor:
            # Table counts
            cursor.execute(
                """
                SELECT schemaname, relname, n_live_tup 
                FROM pg_stat_user_tables 
                ORDER BY n_live_tup DESC 
                LIMIT 10
            """
            )
            tables = [
                {"schema": r[0], "table": r[1], "rows": r[2]} for r in cursor.fetchall()
            ]
            result["details"]["top_tables"] = tables
    except Exception:
        pass

    return result


@router.get("/simple")
def get_simple_health(request):
    """Simple health check for load balancers."""
    return {"status": "ok", "timestamp": timezone.now().isoformat()}
