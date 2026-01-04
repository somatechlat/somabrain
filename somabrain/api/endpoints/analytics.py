"""
Tenant Analytics API Endpoints.

Usage analytics and metrics for individual tenants.

ALL 10 PERSONAS per VIBE Coding Rules:
- 🔒 Security: Tenant isolation enforced
- 🏛️ Architect: Clean analytics patterns
- 💾 DBA: Efficient time-series queries
- 🐍 Django: Native ORM with aggregations
- 📚 Docs: Comprehensive docstrings
- 🧪 QA: Testable interfaces
- 🚨 SRE: Metrics for monitoring
- 📊 Perf: Indexed queries
- 🎨 UX: Dashboard-ready data
- 🛠️ DevOps: Usage tracking
"""

from typing import List, Optional
from datetime import datetime, timedelta
from uuid import UUID

from django.db.models import Count, Sum, Avg, Max, Min, Q
from django.db.models.functions import TruncDate, TruncHour
from django.utils import timezone
from django.shortcuts import get_object_or_404
from ninja import Router, Schema

from somabrain.saas.models import (
    Tenant,
    UsageRecord,
    APIKey,
    AuditLog,
)
from somabrain.saas.auth import require_auth, AuthenticatedRequest
from somabrain.saas.granular import require_permission, Permission


router = Router(tags=["Tenant Analytics"])


# =============================================================================
# SCHEMAS
# =============================================================================

class UsageSummaryOut(Schema):
    """Summary of tenant usage."""
    tenant_id: UUID
    tenant_name: str
    
    # Current period
    api_calls_total: int
    memory_ops_total: int
    unique_metrics: int
    
    # Period info
    period_start: str
    period_end: str
    
    # Trends
    vs_last_period_pct: Optional[float]


class MetricBreakdownOut(Schema):
    """Breakdown by metric type."""
    metric_name: str
    total_quantity: int
    event_count: int
    first_seen: str
    last_seen: str


class HourlyUsageOut(Schema):
    """Hourly usage for charts."""
    hour: str
    quantity: int


class DailyUsageOut(Schema):
    """Daily usage for charts."""
    date: str
    quantity: int


class APIKeyUsageOut(Schema):
    """Usage per API key."""
    key_id: UUID
    key_prefix: str
    key_name: Optional[str]
    request_count: int
    last_used: Optional[str]


class TopEndpointOut(Schema):
    """Top endpoint usage."""
    endpoint: str
    count: int


class UsageQuotaOut(Schema):
    """Current usage vs quota."""
    tenant_id: UUID
    metric: str
    current_usage: int
    quota_limit: int
    usage_percent: float
    reset_date: Optional[str]


# =============================================================================
# USAGE ENDPOINTS
# =============================================================================

@router.get("/{tenant_id}/usage/summary", response=UsageSummaryOut)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.BILLING_READ.value)
def get_usage_summary(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    days: int = 30,
):
    """
    Get usage summary for a tenant.
    
    ALL 10 PERSONAS:
    - DBA: Efficient aggregate query
    - Security: Tenant isolation
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    tenant = get_object_or_404(Tenant, id=tenant_id)
    
    now = timezone.now()
    period_start = now - timedelta(days=days)
    prev_period_start = period_start - timedelta(days=days)
    
    # Current period aggregates
    current_usage = UsageRecord.objects.filter(
        tenant=tenant,
        recorded_at__gte=period_start,
    ).aggregate(
        api_calls=Sum("quantity", filter=Q(metric_name="api_call")),
        memory_ops=Sum("quantity", filter=Q(metric_name="memory_operation")),
        unique_metrics=Count("metric_name", distinct=True),
    )
    
    # Previous period for comparison
    prev_usage = UsageRecord.objects.filter(
        tenant=tenant,
        recorded_at__gte=prev_period_start,
        recorded_at__lt=period_start,
    ).aggregate(total=Sum("quantity"))
    
    current_total = (current_usage["api_calls"] or 0) + (current_usage["memory_ops"] or 0)
    prev_total = prev_usage["total"] or 0
    
    vs_last = None
    if prev_total > 0:
        vs_last = round(((current_total - prev_total) / prev_total) * 100, 1)
    
    return UsageSummaryOut(
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        api_calls_total=current_usage["api_calls"] or 0,
        memory_ops_total=current_usage["memory_ops"] or 0,
        unique_metrics=current_usage["unique_metrics"] or 0,
        period_start=period_start.isoformat(),
        period_end=now.isoformat(),
        vs_last_period_pct=vs_last,
    )


@router.get("/{tenant_id}/usage/breakdown", response=List[MetricBreakdownOut])
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.BILLING_READ.value)
def get_usage_breakdown(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    days: int = 30,
):
    """Get usage breakdown by metric type."""
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    period_start = timezone.now() - timedelta(days=days)
    
    breakdown = (
        UsageRecord.objects.filter(tenant_id=tenant_id, recorded_at__gte=period_start)
        .values("metric_name")
        .annotate(
            total_quantity=Sum("quantity"),
            event_count=Count("id"),
            first_seen=Min("recorded_at"),
            last_seen=Max("recorded_at"),
        )
        .order_by("-total_quantity")
    )
    
    return [
        MetricBreakdownOut(
            metric_name=item["metric_name"],
            total_quantity=item["total_quantity"],
            event_count=item["event_count"],
            first_seen=item["first_seen"].isoformat(),
            last_seen=item["last_seen"].isoformat(),
        )
        for item in breakdown
    ]


@router.get("/{tenant_id}/usage/hourly", response=List[HourlyUsageOut])
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.BILLING_READ.value)
def get_hourly_usage(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    hours: int = 24,
):
    """Get hourly usage for the last N hours."""
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    period_start = timezone.now() - timedelta(hours=hours)
    
    hourly = (
        UsageRecord.objects.filter(tenant_id=tenant_id, recorded_at__gte=period_start)
        .annotate(hour=TruncHour("recorded_at"))
        .values("hour")
        .annotate(quantity=Sum("quantity"))
        .order_by("hour")
    )
    
    return [
        HourlyUsageOut(
            hour=item["hour"].isoformat(),
            quantity=item["quantity"] or 0,
        )
        for item in hourly
    ]


@router.get("/{tenant_id}/usage/daily", response=List[DailyUsageOut])
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.BILLING_READ.value)
def get_daily_usage(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    days: int = 30,
):
    """Get daily usage for the last N days."""
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    period_start = timezone.now() - timedelta(days=days)
    
    daily = (
        UsageRecord.objects.filter(tenant_id=tenant_id, recorded_at__gte=period_start)
        .annotate(date=TruncDate("recorded_at"))
        .values("date")
        .annotate(quantity=Sum("quantity"))
        .order_by("date")
    )
    
    return [
        DailyUsageOut(
            date=item["date"].isoformat(),
            quantity=item["quantity"] or 0,
        )
        for item in daily
    ]


@router.get("/{tenant_id}/api-keys/usage", response=List[APIKeyUsageOut])
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.API_KEYS_READ.value)
def get_api_key_usage(
    request: AuthenticatedRequest,
    tenant_id: UUID,
):
    """Get usage statistics per API key."""
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    keys = APIKey.objects.filter(tenant_id=tenant_id).annotate(
        request_count=Count("id"),  # Placeholder - would track via logs
    )
    
    return [
        APIKeyUsageOut(
            key_id=key.id,
            key_prefix=key.key_prefix,
            key_name=key.name,
            request_count=key.request_count,
            last_used=key.last_used_at.isoformat() if key.last_used_at else None,
        )
        for key in keys
    ]


@router.get("/{tenant_id}/quota", response=List[UsageQuotaOut])
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.BILLING_READ.value)
def get_usage_quota(
    request: AuthenticatedRequest,
    tenant_id: UUID,
):
    """
    Get current usage vs quota limits.
    
    ALL 10 PERSONAS:
    - Billing: Quota tracking
    - UX: Clear usage indicators
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    tenant = get_object_or_404(Tenant, id=tenant_id)
    
    # Get quota from subscription tier
    subscription = getattr(tenant, "subscription", None)
    if not subscription or not subscription.tier:
        return []
    
    tier = subscription.tier
    now = timezone.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Current month usage
    current_usage = UsageRecord.objects.filter(
        tenant=tenant,
        recorded_at__gte=month_start,
    ).aggregate(
        api_calls=Sum("quantity", filter=Q(metric_name="api_call")),
        memory_ops=Sum("quantity", filter=Q(metric_name="memory_operation")),
    )
    
    quotas = []
    
    # API calls quota
    api_usage = current_usage["api_calls"] or 0
    api_limit = tier.api_calls_limit
    quotas.append(UsageQuotaOut(
        tenant_id=tenant.id,
        metric="api_calls",
        current_usage=api_usage,
        quota_limit=api_limit,
        usage_percent=round((api_usage / api_limit) * 100, 1) if api_limit > 0 else 0,
        reset_date=(month_start + timedelta(days=32)).replace(day=1).isoformat(),
    ))
    
    # Memory ops quota
    mem_usage = current_usage["memory_ops"] or 0
    mem_limit = tier.memory_ops_limit
    quotas.append(UsageQuotaOut(
        tenant_id=tenant.id,
        metric="memory_operations",
        current_usage=mem_usage,
        quota_limit=mem_limit,
        usage_percent=round((mem_usage / mem_limit) * 100, 1) if mem_limit > 0 else 0,
        reset_date=(month_start + timedelta(days=32)).replace(day=1).isoformat(),
    ))
    
    return quotas