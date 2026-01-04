"""
System Metrics API for SomaBrain.

Platform metrics with real Django ORM aggregations.
Uses REAL Django ORM - NO mocks, NO fallbacks.

ALL 10 PERSONAS - VIBE Coding Rules:
- 🔒 Security: Admin only metrics
- 🏛️ Architect: Clean metrics patterns
- 💾 DBA: Real Django ORM aggregations
- 🐍 Django Expert: Native Django patterns
- 📚 Technical Writer: Metrics documentation
- 🧪 QA Engineer: Metrics validation
- 🚨 SRE: System monitoring
- 📊 Performance: Efficient aggregations
- 🎨 UX: Clear metrics display
- 🛠️ DevOps: Platform observability
"""

from typing import List, Optional
from datetime import datetime, timedelta

from django.utils import timezone
from django.db.models import Count, Sum, Avg
from django.db.models.functions import TruncDate, TruncHour
from ninja import Router, Schema
from ninja.errors import HttpError

from somabrain.saas.models import (
    Tenant, 
    TenantUser,
    APIKey,
    AuditLog,
)
from somabrain.saas.auth import require_auth, AuthenticatedRequest
from somabrain.saas.granular import require_permission, Permission


router = Router(tags=["System Metrics"])


# =============================================================================
# SCHEMAS
# =============================================================================

class PlatformMetrics(Schema):
    """Platform-wide metrics."""
    total_tenants: int
    active_tenants: int
    total_users: int
    active_users: int
    total_api_keys: int
    active_api_keys: int
    audit_logs_today: int
    timestamp: str


class TenantGrowth(Schema):
    """Tenant growth data."""
    date: str
    new_tenants: int
    cumulative: int


class UserActivity(Schema):
    """User activity metrics."""
    hour: str
    active_users: int
    api_calls: int


class ApiUsage(Schema):
    """API usage metrics."""
    date: str
    total_calls: int
    unique_users: int


# =============================================================================
# PLATFORM METRICS
# =============================================================================

@router.get("/platform", response=PlatformMetrics)
@require_auth(roles=["super-admin"])
@require_permission(Permission.PLATFORM_MANAGE.value)
def get_platform_metrics(request: AuthenticatedRequest):
    """
    Get platform-wide metrics.
    
    📊 Performance: REAL ORM counts
    
    REAL Django ORM aggregations.
    """
    now = timezone.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    last_30_days = now - timedelta(days=30)
    
    # REAL counts
    total_tenants = Tenant.objects.count()
    active_tenants = Tenant.objects.filter(status="active").count()
    total_users = TenantUser.objects.count()
    active_users = TenantUser.objects.filter(
        is_active=True,
        last_login_at__gte=last_30_days
    ).count()
    total_api_keys = APIKey.objects.count()
    active_api_keys = APIKey.objects.filter(is_active=True).count()
    audit_logs_today = AuditLog.objects.filter(timestamp__gte=today).count()
    
    return PlatformMetrics(
        total_tenants=total_tenants,
        active_tenants=active_tenants,
        total_users=total_users,
        active_users=active_users,
        total_api_keys=total_api_keys,
        active_api_keys=active_api_keys,
        audit_logs_today=audit_logs_today,
        timestamp=now.isoformat(),
    )


@router.get("/tenant-growth", response=List[TenantGrowth])
@require_auth(roles=["super-admin"])
@require_permission(Permission.PLATFORM_MANAGE.value)
def get_tenant_growth(
    request: AuthenticatedRequest,
    days: int = 30,
):
    """
    Get tenant growth over time.
    
    📊 Performance: REAL aggregations
    
    REAL Django ORM with TruncDate.
    """
    since = timezone.now() - timedelta(days=days)
    
    # REAL daily aggregation
    daily_counts = Tenant.objects.filter(
        created_at__gte=since
    ).annotate(
        date=TruncDate("created_at")
    ).values("date").annotate(
        count=Count("id")
    ).order_by("date")
    
    result = []
    cumulative = Tenant.objects.filter(created_at__lt=since).count()
    
    for row in daily_counts:
        cumulative += row["count"]
        result.append(TenantGrowth(
            date=row["date"].isoformat() if row["date"] else "",
            new_tenants=row["count"],
            cumulative=cumulative,
        ))
    
    return result


@router.get("/user-activity", response=List[UserActivity])
@require_auth(roles=["super-admin"])
@require_permission(Permission.PLATFORM_MANAGE.value)
def get_user_activity(
    request: AuthenticatedRequest,
    hours: int = 24,
):
    """
    Get hourly user activity.
    
    📊 Performance: REAL hourly aggregations
    
    REAL Django ORM with TruncHour.
    """
    since = timezone.now() - timedelta(hours=hours)
    
    # REAL hourly aggregation from audit logs
    hourly_activity = AuditLog.objects.filter(
        timestamp__gte=since
    ).annotate(
        hour=TruncHour("timestamp")
    ).values("hour").annotate(
        calls=Count("id"),
        users=Count("actor_id", distinct=True)
    ).order_by("hour")
    
    return [
        UserActivity(
            hour=row["hour"].isoformat() if row["hour"] else "",
            active_users=row["users"],
            api_calls=row["calls"],
        )
        for row in hourly_activity
    ]


@router.get("/api-usage", response=List[ApiUsage])
@require_auth(roles=["super-admin"])
@require_permission(Permission.PLATFORM_MANAGE.value)
def get_api_usage(
    request: AuthenticatedRequest,
    days: int = 14,
):
    """
    Get daily API usage.
    
    📊 Performance: REAL daily aggregations
    
    REAL Django ORM aggregations.
    """
    since = timezone.now() - timedelta(days=days)
    
    # REAL daily aggregation
    daily_usage = AuditLog.objects.filter(
        timestamp__gte=since,
        action__startswith="api."
    ).annotate(
        date=TruncDate("timestamp")
    ).values("date").annotate(
        total=Count("id"),
        users=Count("actor_id", distinct=True)
    ).order_by("date")
    
    return [
        ApiUsage(
            date=row["date"].isoformat() if row["date"] else "",
            total_calls=row["total"],
            unique_users=row["users"],
        )
        for row in daily_usage
    ]


# =============================================================================
# TENANT METRICS
# =============================================================================

@router.get("/tenant/{tenant_id}/metrics")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
def get_tenant_metrics(
    request: AuthenticatedRequest,
    tenant_id: str,
):
    """
    Get metrics for a specific tenant.
    
    📊 Performance: REAL tenant counts
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != tenant_id:
            raise HttpError(403, "Access denied")
    
    now = timezone.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    last_7_days = now - timedelta(days=7)
    
    # REAL counts
    return {
        "tenant_id": tenant_id,
        "users": {
            "total": TenantUser.objects.filter(tenant_id=tenant_id).count(),
            "active": TenantUser.objects.filter(tenant_id=tenant_id, is_active=True).count(),
        },
        "api_keys": {
            "total": APIKey.objects.filter(tenant_id=tenant_id).count(),
            "active": APIKey.objects.filter(tenant_id=tenant_id, is_active=True).count(),
        },
        "audit_logs": {
            "today": AuditLog.objects.filter(tenant_id=tenant_id, timestamp__gte=today).count(),
            "week": AuditLog.objects.filter(tenant_id=tenant_id, timestamp__gte=last_7_days).count(),
        },
        "timestamp": now.isoformat(),
    }


@router.get("/top-tenants")
@require_auth(roles=["super-admin"])
@require_permission(Permission.PLATFORM_MANAGE.value)
def get_top_tenants(
    request: AuthenticatedRequest,
    limit: int = 10,
    metric: str = "users",
):
    """
    Get top tenants by metric.
    
    📊 Performance: REAL rankings
    """
    if metric == "users":
        tenants = Tenant.objects.annotate(
            count=Count("users")
        ).order_by("-count")[:limit]
        
        return {
            "metric": "users",
            "tenants": [
                {"tenant_id": str(t.id), "name": t.name, "count": t.count}
                for t in tenants
            ]
        }
    elif metric == "api_keys":
        tenants = Tenant.objects.annotate(
            count=Count("api_keys")
        ).order_by("-count")[:limit]
        
        return {
            "metric": "api_keys",
            "tenants": [
                {"tenant_id": str(t.id), "name": t.name, "count": t.count}
                for t in tenants
            ]
        }
    else:
        raise HttpError(400, f"Invalid metric: {metric}")