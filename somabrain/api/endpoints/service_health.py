"""
Service Health Monitoring API for SomaBrain.

Real infrastructure health checks with Django.
Uses REAL service checks - NO mocks, NO fallbacks.

ALL 10 PERSONAS - VIBE Coding Rules:
- 🔒 Security: Health check access control
- 🏛️ Architect: Clean health patterns
- 💾 DBA: Real database checks
- 🐍 Django Expert: Native Django patterns
- 📚 Technical Writer: Health documentation
- 🧪 QA Engineer: Health validation
- 🚨 SRE: Infrastructure monitoring
- 📊 Performance: Response time tracking
- 🎨 UX: Clear health status
- 🛠️ DevOps: Service lifecycle
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID
import time

from django.utils import timezone
from django.db import connection
from django.core.cache import cache
from ninja import Router, Schema
from ninja.errors import HttpError

from somabrain.saas.models import Tenant, AuditLog
from somabrain.saas.auth import require_auth, AuthenticatedRequest
from somabrain.saas.granular import require_permission, Permission


router = Router(tags=["Service Health"])


# =============================================================================
# SCHEMAS
# =============================================================================

class ServiceStatus(Schema):
    """Individual service status."""
    name: str
    status: str  # healthy, degraded, unhealthy
    response_time_ms: float
    message: Optional[str]
    last_check: str


class HealthSummary(Schema):
    """Overall health summary."""
    status: str
    services: List[ServiceStatus]
    timestamp: str
    uptime_seconds: int


class HealthHistory(Schema):
    """Health check history entry."""
    timestamp: str
    status: str
    response_time_ms: float


# =============================================================================
# REAL HEALTH CHECKS
# =============================================================================

def check_database() -> ServiceStatus:
    """Check REAL PostgreSQL database."""
    start = time.time()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        response_time = (time.time() - start) * 1000
        return ServiceStatus(
            name="database",
            status="healthy" if response_time < 100 else "degraded",
            response_time_ms=round(response_time, 2),
            message=None,
            last_check=timezone.now().isoformat(),
        )
    except Exception as e:
        return ServiceStatus(
            name="database",
            status="unhealthy",
            response_time_ms=0,
            message=str(e),
            last_check=timezone.now().isoformat(),
        )


def check_cache() -> ServiceStatus:
    """Check REAL Redis/cache."""
    start = time.time()
    try:
        test_key = "health:cache:test"
        cache.set(test_key, "ok", timeout=10)
        result = cache.get(test_key)
        cache.delete(test_key)
        
        response_time = (time.time() - start) * 1000
        
        if result == "ok":
            return ServiceStatus(
                name="cache",
                status="healthy" if response_time < 50 else "degraded",
                response_time_ms=round(response_time, 2),
                message=None,
                last_check=timezone.now().isoformat(),
            )
        else:
            return ServiceStatus(
                name="cache",
                status="unhealthy",
                response_time_ms=round(response_time, 2),
                message="Cache read/write failed",
                last_check=timezone.now().isoformat(),
            )
    except Exception as e:
        return ServiceStatus(
            name="cache",
            status="unhealthy",
            response_time_ms=0,
            message=str(e),
            last_check=timezone.now().isoformat(),
        )


def check_orm() -> ServiceStatus:
    """Check REAL Django ORM with actual query."""
    start = time.time()
    try:
        # REAL query against Tenant model
        count = Tenant.objects.count()
        response_time = (time.time() - start) * 1000
        
        return ServiceStatus(
            name="orm",
            status="healthy" if response_time < 100 else "degraded",
            response_time_ms=round(response_time, 2),
            message=f"{count} tenants",
            last_check=timezone.now().isoformat(),
        )
    except Exception as e:
        return ServiceStatus(
            name="orm",
            status="unhealthy",
            response_time_ms=0,
            message=str(e),
            last_check=timezone.now().isoformat(),
        )


# =============================================================================
# PUBLIC ENDPOINTS
# =============================================================================

@router.get("/health", response=HealthSummary)
def get_health():
    """
    Get overall system health.
    
    🚨 SRE: Primary health endpoint
    
    REAL checks against database, cache, ORM.
    """
    # Run REAL checks
    db_status = check_database()
    cache_status = check_cache()
    orm_status = check_orm()
    
    services = [db_status, cache_status, orm_status]
    
    # Determine overall status
    if any(s.status == "unhealthy" for s in services):
        overall = "unhealthy"
    elif any(s.status == "degraded" for s in services):
        overall = "degraded"
    else:
        overall = "healthy"
    
    # Calculate uptime from cache
    startup_time = cache.get("system:startup_time")
    if not startup_time:
        startup_time = timezone.now()
        cache.set("system:startup_time", startup_time, timeout=86400 * 30)
    
    uptime = int((timezone.now() - startup_time).total_seconds()) if isinstance(startup_time, datetime) else 0
    
    return HealthSummary(
        status=overall,
        services=services,
        timestamp=timezone.now().isoformat(),
        uptime_seconds=uptime,
    )


@router.get("/liveness")
def liveness_check():
    """
    Kubernetes liveness probe.
    
    🛠️ DevOps: K8s probe
    """
    return {"status": "alive", "timestamp": timezone.now().isoformat()}


@router.get("/readiness")
def readiness_check():
    """
    Kubernetes readiness probe.
    
    🛠️ DevOps: K8s probe
    
    REAL database check.
    """
    db_status = check_database()
    
    if db_status.status == "unhealthy":
        raise HttpError(503, "Database unavailable")
    
    return {"status": "ready", "timestamp": timezone.now().isoformat()}


# =============================================================================
# ADMIN ENDPOINTS
# =============================================================================

@router.get("/services", response=List[ServiceStatus])
@require_auth(roles=["super-admin"])
def list_service_status(request: AuthenticatedRequest):
    """
    List all service statuses (admin).
    
    🚨 SRE: Service monitoring
    
    REAL checks.
    """
    return [
        check_database(),
        check_cache(),
        check_orm(),
    ]


@router.get("/services/{service_name}", response=ServiceStatus)
@require_auth(roles=["super-admin"])
def get_service_status(
    request: AuthenticatedRequest,
    service_name: str,
):
    """Get specific service status."""
    checks = {
        "database": check_database,
        "cache": check_cache,
        "orm": check_orm,
    }
    
    if service_name not in checks:
        raise HttpError(404, f"Unknown service: {service_name}")
    
    return checks[service_name]()


@router.get("/history/{service_name}", response=List[HealthHistory])
@require_auth(roles=["super-admin"])
def get_health_history(
    request: AuthenticatedRequest,
    service_name: str,
    hours: int = 24,
):
    """
    Get health check history.
    
    📊 Performance: Historical health data
    
    REAL data from cache.
    """
    history_key = f"health:history:{service_name}"
    history = cache.get(history_key, [])
    
    # Filter by time range
    since = timezone.now() - timedelta(hours=hours)
    
    return [
        HealthHistory(
            timestamp=h["timestamp"],
            status=h["status"],
            response_time_ms=h["response_time_ms"],
        )
        for h in history
        if datetime.fromisoformat(h["timestamp"]) > since
    ][:100]


@router.get("/metrics")
@require_auth(roles=["super-admin"])
@require_permission(Permission.PLATFORM_MANAGE.value)
def get_health_metrics(request: AuthenticatedRequest):
    """
    Get detailed health metrics.
    
    📊 Performance: REAL metrics
    """
    # REAL counts
    tenant_count = Tenant.objects.count()
    active_tenants = Tenant.objects.filter(status="active").count()
    
    # Get last audit log
    last_activity = AuditLog.objects.order_by("-timestamp").first()
    
    return {
        "tenants": {
            "total": tenant_count,
            "active": active_tenants,
        },
        "last_activity": last_activity.timestamp.isoformat() if last_activity else None,
        "database_status": check_database().status,
        "cache_status": check_cache().status,
        "timestamp": timezone.now().isoformat(),
    }


@router.post("/check-all")
@require_auth(roles=["super-admin"])
def force_health_check(request: AuthenticatedRequest):
    """
    Force immediate health check on all services.
    
    🧪 QA: On-demand health check
    """
    results = {
        "database": check_database().dict(),
        "cache": check_cache().dict(),
        "orm": check_orm().dict(),
    }
    
    # Store in history
    for name, result in results.items():
        history_key = f"health:history:{name}"
        history = cache.get(history_key, [])
        history.insert(0, {
            "timestamp": result["last_check"],
            "status": result["status"],
            "response_time_ms": result["response_time_ms"],
        })
        history = history[:100]  # Keep last 100
        cache.set(history_key, history, timeout=86400 * 7)
    
    return {"checked": True, "results": results}
