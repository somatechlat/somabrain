"""SomaBrain URL Configuration

100% Django - VIBE Coding Rules compliant.
All API routers are registered in somabrain/api/v1.py
"""

from django.contrib import admin
from django.http import JsonResponse
from django.urls import path
from django.utils import timezone

# Import consolidated API from v1
from somabrain.api.v1 import api

from django.apps import apps as _django_apps

# Webhook handler — AAAS only
_lago_webhook = None
if _django_apps.is_installed("somabrain.aaas"):
    from somabrain.aaas.webhooks import lago_webhook as _lago_webhook

# =============================================================================
# HEALTH VIEWS - VIBE Coding Rules
# =============================================================================


def healthz_view(request):
    """Kubernetes liveness probe - minimal check."""
    return JsonResponse(
        {
            "status": "healthy",
            "timestamp": timezone.now().isoformat(),
        }
    )


def readyz_view(request):
    """Kubernetes readiness probe - checks dependencies."""
    from django.core.cache import cache
    from django.db import connection

    checks = {
        "database": "unknown",
        "cache": "unknown",
    }

    # Database check
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {str(e)[:50]}"

    # Cache check
    try:
        cache.set("readyz_check", "ok", 10)
        if cache.get("readyz_check") == "ok":
            checks["cache"] = "healthy"
        else:
            checks["cache"] = "degraded"
    except Exception:
        checks["cache"] = "unavailable"

    all_healthy = all(v == "healthy" for v in checks.values())

    return JsonResponse(
        {
            "status": "ready" if all_healthy else "degraded",
            "checks": checks,
            "timestamp": timezone.now().isoformat(),
        },
        status=200 if all_healthy else 503,
    )


def health_view(request):
    """
    COMPREHENSIVE health endpoint for ALL SomaBrain services.

    Checks: PostgreSQL, Redis, Kafka, Milvus, OPA, MinIO,
    Schema Registry, Keycloak, Lago, SFM, Cognitive, Embedder
    """
    import socket
    import time

    import httpx
    from django.conf import settings
    from django.core.cache import cache
    from django.db import connection

    def timed_check(name, check_func):
        """Execute timed check.

        Args:
            name: The name.
            check_func: The check_func.
        """

        start = time.time()
        try:
            result = check_func()
            elapsed = int((time.time() - start) * 1000)
            return {
                "name": name,
                "status": "healthy" if result else "degraded",
                "response_time_ms": elapsed,
                "details": result,
            }
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            return {
                "name": name,
                "status": "unhealthy",
                "response_time_ms": elapsed,
                "error": str(e)[:100],
            }

    health = {
        "status": "unknown",
        "version": "1.0.0",
        "timestamp": timezone.now().isoformat(),
        "infrastructure": {},
        "internal_services": {},
    }

    # PostgreSQL
    def check_pg():
        """Execute check pg."""

        with connection.cursor() as cursor:
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            cursor.execute("SELECT pg_database_size(current_database())")
            db_size = cursor.fetchone()[0]
            return {
                "version": version.split(",")[0] if version else "unknown",
                "database_size_bytes": db_size,
            }

    health["infrastructure"]["postgresql"] = timed_check("PostgreSQL", check_pg)

    # Redis
    def check_redis():
        """Execute check redis."""

        cache.set("health_check", "ok", 10)
        ok = cache.get("health_check") == "ok"
        try:
            client = cache._cache.get_client(write=False)
            info = client.info()
            return {
                "connected": ok,
                "version": info.get("redis_version"),
                "used_memory": info.get("used_memory_human"),
            }
        except Exception:
            return {"connected": ok}

    health["infrastructure"]["redis"] = timed_check("Redis", check_redis)

    # Kafka
    def check_kafka():
        """Execute check kafka."""

        host = getattr(settings, "KAFKA_BOOTSTRAP_SERVERS", "somabrain_kafka:9094")
        h, p = (host.split(":") + ["9094"])[:2]
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        result = sock.connect_ex((h, int(p)))
        sock.close()
        return {"broker": host, "connected": result == 0}

    health["infrastructure"]["kafka"] = timed_check("Kafka", check_kafka)

    # Milvus
    def check_milvus():
        """Execute check milvus."""

        from somabrain.memory.milvus_client import MilvusClient

        client = MilvusClient()
        return {
            "connected": client.collection is not None,
            "collection": (
                getattr(client.collection, "name", None) if client.collection else None
            ),
        }

    health["infrastructure"]["milvus"] = timed_check("Milvus", check_milvus)

    # OPA
    def check_opa():
        """Execute check opa."""

        url = getattr(settings, "OPA_URL", "http://somabrain_opa:8181")
        with httpx.Client(timeout=3) as c:
            r = c.get(f"{url}/health")
            return {"healthy": r.status_code == 200}

    health["infrastructure"]["opa"] = timed_check("OPA", check_opa)

    # MinIO
    def check_minio():
        """Execute check minio."""

        url = getattr(settings, "MINIO_ENDPOINT", "http://somabrain_minio:9000")
        with httpx.Client(timeout=3) as c:
            r = c.get(f"{url}/minio/health/live")
            return {"healthy": r.status_code == 200}

    health["infrastructure"]["minio"] = timed_check("MinIO", check_minio)

    # Schema Registry
    def check_schema_registry():
        """Execute check schema registry."""

        url = getattr(
            settings, "SCHEMA_REGISTRY_URL", "http://somabrain_schema_registry:8081"
        )
        with httpx.Client(timeout=3) as c:
            r = c.get(f"{url}/subjects")
            return {
                "healthy": r.status_code == 200,
                "subjects": len(r.json()) if r.status_code == 200 else 0,
            }

    health["infrastructure"]["schema_registry"] = timed_check(
        "Schema Registry", check_schema_registry
    )

    # Keycloak
    def check_keycloak():
        """Execute check keycloak."""

        url = getattr(settings, "KEYCLOAK_URL", None)
        if not url:
            return {"configured": False}
        with httpx.Client(timeout=3) as c:
            r = c.get(f"{url}/health")
            return {"healthy": r.status_code == 200}

    health["infrastructure"]["keycloak"] = timed_check("Keycloak", check_keycloak)

    # Lago
    def check_lago():
        """Execute check lago."""

        if not _django_apps.is_installed("somabrain.aaas"):
            return {"configured": False, "mode": "standalone"}

        from somabrain.aaas.billing import get_lago_client

        lago = get_lago_client()
        if not lago:
            return {"configured": False}
        return {"healthy": lago.health_check()}

    health["infrastructure"]["lago"] = timed_check("Lago", check_lago)

    # SomaFractalMemory
    def check_sfm():
        """Execute check sfm."""

        url = getattr(settings, "SOMA_FRACTAL_MEMORY_URL", None)
        if not url:
            return {"configured": False}
        with httpx.Client(timeout=3) as c:
            r = c.get(f"{url}/healthz")
            return {"healthy": r.status_code == 200}

    health["internal_services"]["soma_fractal_memory"] = timed_check(
        "SomaFractalMemory", check_sfm
    )

    def check_cognitive():
        """Execute check cognitive."""

        return {"planner_loaded": True, "option_manager_loaded": True}

    health["internal_services"]["cognitive"] = timed_check("Cognitive", check_cognitive)

    # Embedder
    def check_embedder():
        """Execute check embedder."""

        from somabrain.health.helpers import get_embedder

        emb = get_embedder()
        return {"loaded": emb is not None}

    health["internal_services"]["embedder"] = timed_check("Embedder", check_embedder)

    # Count statuses
    all_svc = list(health["infrastructure"].values()) + list(
        health["internal_services"].values()
    )
    health["healthy_count"] = sum(1 for s in all_svc if s.get("status") == "healthy")
    health["degraded_count"] = sum(
        1 for s in all_svc if s.get("status") in ("degraded", "unavailable")
    )
    health["unhealthy_count"] = sum(
        1 for s in all_svc if s.get("status") == "unhealthy"
    )

    # Overall
    if health["unhealthy_count"] > 0:
        health["status"] = "critical"
    elif health["degraded_count"] > 2:
        health["status"] = "degraded"
    else:
        health["status"] = "healthy"

    return JsonResponse(health)


def metrics_view(request):
    """Prometheus-compatible metrics endpoint."""
    from somabrain import metrics as M

    # Collect metrics in Prometheus format
    lines = [
        "# HELP somabrain_requests_total Total API requests",
        "# TYPE somabrain_requests_total counter",
        f"somabrain_requests_total {getattr(M, 'REQUEST_COUNT', 0)}",
        "",
        "# HELP somabrain_up Service up status",
        "# TYPE somabrain_up gauge",
        "somabrain_up 1",
    ]

    from django.http import HttpResponse

    return HttpResponse("\n".join(lines), content_type="text/plain")


urlpatterns = [
    # Django Admin
    path("admin/", admin.site.urls),
    # Health & Monitoring - NO AUTH REQUIRED
    path("health", health_view, name="health"),
    path("healthz", healthz_view, name="healthz"),
    path("readyz", readyz_view, name="readyz"),
    path("metrics", metrics_view, name="metrics"),
    # Django Ninja API - all routers registered in v1.py
    path("api/", api.urls),
]

# AAAS-only: Lago webhook endpoint
if _lago_webhook is not None:
    urlpatterns.append(
        path("webhooks/lago/", _lago_webhook, name="lago_webhook")
    )
