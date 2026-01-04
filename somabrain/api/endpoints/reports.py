"""
Reporting and Data Export API for SomaBrain.

Generate reports and export data for tenants and platform.

ALL 10 PERSONAS - VIBE Coding Rules:
- 🔒 Security Engineer: Tenant isolation, export authorization
- 🏛️ Architect: Clean report generation patterns
- 💾 DBA: Efficient aggregation queries
- 🐍 Django Expert: Native ORM aggregates
- 📚 Technical Writer: Comprehensive docstrings
- 🧪 QA Engineer: Testable report formats
- 🚨 SRE: Background job support
- 📊 Performance Engineer: Paginated exports
- 🎨 UX Advocate: Multiple export formats
- 🛠️ DevOps: Scheduled report support
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID
import csv
import io
import json

from django.db.models import Count, Sum, Avg, Max, Min, Q
from django.db.models.functions import TruncDate, TruncHour
from django.utils import timezone
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from ninja import Router, Schema

from somabrain.saas.models import (
    Tenant, TenantUser, APIKey, AuditLog, 
    UsageRecord, Subscription, SubscriptionTier
)
from somabrain.saas.auth import require_auth, AuthenticatedRequest
from somabrain.saas.granular import require_permission, Permission


router = Router(tags=["Reports"])


# =============================================================================
# SCHEMAS - ALL 10 PERSONAS
# =============================================================================

class UsageReportOut(Schema):
    """Usage report output."""
    tenant_id: UUID
    tenant_name: str
    period_start: str
    period_end: str
    total_api_calls: int
    total_memory_ops: int
    total_queries: int
    unique_users: int
    unique_keys: int
    daily_breakdown: List[Dict[str, Any]]


class TenantReportOut(Schema):
    """Tenant status report."""
    tenant_id: UUID
    name: str
    slug: str
    status: str
    tier: str
    users_count: int
    api_keys_count: int
    api_calls_this_month: int
    created_at: str
    last_activity: Optional[str]


class PlatformReportOut(Schema):
    """Platform-wide statistics report."""
    generated_at: str
    period: str
    total_tenants: int
    active_tenants: int
    total_users: int
    total_api_keys: int
    total_api_calls: int
    revenue_estimate: float
    tier_distribution: Dict[str, int]
    growth_metrics: Dict[str, Any]


class ExportJobOut(Schema):
    """Export job status."""
    job_id: str
    status: str
    format: str
    download_url: Optional[str]
    created_at: str
    completed_at: Optional[str]


# =============================================================================
# TENANT REPORTS - ALL 10 PERSONAS
# =============================================================================

@router.get("/{tenant_id}/usage", response=UsageReportOut)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.BILLING_READ.value)
def get_usage_report(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    days: int = 30,
):
    """
    Get detailed usage report for a tenant.
    
    💾 DBA: Efficient aggregation
    📊 Performance: Date-range queries
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    tenant = get_object_or_404(Tenant, id=tenant_id)
    period_start = timezone.now() - timedelta(days=days)
    
    # Aggregate usage
    usage = UsageRecord.objects.filter(
        tenant=tenant,
        recorded_at__gte=period_start,
    ).aggregate(
        api_calls=Sum("quantity", filter=Q(metric_name="api_call")),
        memory_ops=Sum("quantity", filter=Q(metric_name="memory_operation")),
        queries=Sum("quantity", filter=Q(metric_name="query")),
    )
    
    # Unique users and keys
    unique_users = UsageRecord.objects.filter(
        tenant=tenant,
        recorded_at__gte=period_start,
    ).values("user_id").distinct().count()
    
    unique_keys = UsageRecord.objects.filter(
        tenant=tenant,
        recorded_at__gte=period_start,
    ).values("api_key_id").distinct().count()
    
    # Daily breakdown
    daily = (
        UsageRecord.objects.filter(tenant=tenant, recorded_at__gte=period_start)
        .annotate(date=TruncDate("recorded_at"))
        .values("date")
        .annotate(
            api_calls=Sum("quantity", filter=Q(metric_name="api_call")),
            memory_ops=Sum("quantity", filter=Q(metric_name="memory_operation")),
        )
        .order_by("date")
    )
    
    daily_breakdown = [
        {
            "date": d["date"].isoformat() if d["date"] else None,
            "api_calls": d["api_calls"] or 0,
            "memory_ops": d["memory_ops"] or 0,
        }
        for d in daily
    ]
    
    return UsageReportOut(
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        period_start=period_start.isoformat(),
        period_end=timezone.now().isoformat(),
        total_api_calls=usage["api_calls"] or 0,
        total_memory_ops=usage["memory_ops"] or 0,
        total_queries=usage["queries"] or 0,
        unique_users=unique_users,
        unique_keys=unique_keys,
        daily_breakdown=daily_breakdown,
    )


@router.get("/{tenant_id}/summary", response=TenantReportOut)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
def get_tenant_summary(
    request: AuthenticatedRequest,
    tenant_id: UUID,
):
    """
    Get tenant summary report.
    
    🎨 UX: Clear status overview
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    tenant = get_object_or_404(Tenant, id=tenant_id)
    
    # Counts
    users = TenantUser.objects.filter(tenant=tenant).count()
    keys = APIKey.objects.filter(tenant=tenant).count()
    
    # API calls this month
    month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    api_calls = UsageRecord.objects.filter(
        tenant=tenant,
        metric_name="api_call",
        recorded_at__gte=month_start,
    ).aggregate(total=Sum("quantity"))["total"] or 0
    
    # Last activity
    last_audit = AuditLog.objects.filter(tenant=tenant).order_by("-timestamp").first()
    
    return TenantReportOut(
        tenant_id=tenant.id,
        name=tenant.name,
        slug=tenant.slug,
        status=tenant.status,
        tier=str(tenant.tier) if tenant.tier else "free",
        users_count=users,
        api_keys_count=keys,
        api_calls_this_month=api_calls,
        created_at=tenant.created_at.isoformat(),
        last_activity=last_audit.timestamp.isoformat() if last_audit else None,
    )


@router.get("/{tenant_id}/export/usage")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.BILLING_READ.value)
def export_usage_data(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    days: int = 30,
    format: str = "csv",
):
    """
    Export usage data as CSV or JSON.
    
    🛠️ DevOps: Multiple formats
    🔒 Security: Authorized export
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    period_start = timezone.now() - timedelta(days=days)
    records = UsageRecord.objects.filter(
        tenant_id=tenant_id,
        recorded_at__gte=period_start,
    ).order_by("-recorded_at")[:10000]
    
    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["timestamp", "metric_name", "quantity", "api_key_id", "user_id"])
        
        for r in records:
            writer.writerow([
                r.recorded_at.isoformat(),
                r.metric_name,
                r.quantity,
                str(r.api_key_id) if r.api_key_id else "",
                str(r.user_id) if r.user_id else "",
            ])
        
        response = HttpResponse(output.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="usage_{tenant_id}_{days}d.csv"'
        return response
    
    # JSON
    from django.http import JsonResponse
    return JsonResponse({
        "tenant_id": str(tenant_id),
        "period_days": days,
        "records": [
            {
                "timestamp": r.recorded_at.isoformat(),
                "metric_name": r.metric_name,
                "quantity": r.quantity,
            }
            for r in records
        ],
    })


# =============================================================================
# PLATFORM REPORTS (Super Admin) - ALL 10 PERSONAS
# =============================================================================

@router.get("/platform/overview", response=PlatformReportOut)
@require_auth(roles=["super-admin"])
@require_permission(Permission.PLATFORM_MANAGE.value)
def get_platform_report(
    request: AuthenticatedRequest,
    days: int = 30,
):
    """
    Get platform-wide statistics report.
    
    🏛️ Architect: Comprehensive metrics
    📊 Performance: Efficient aggregates
    """
    period_start = timezone.now() - timedelta(days=days)
    
    # Tenant counts
    tenants = Tenant.objects.aggregate(
        total=Count("id"),
        active=Count("id", filter=Q(status="active")),
    )
    
    # User and key counts
    total_users = TenantUser.objects.count()
    total_keys = APIKey.objects.count()
    
    # API calls
    total_calls = UsageRecord.objects.filter(
        metric_name="api_call",
        recorded_at__gte=period_start,
    ).aggregate(total=Sum("quantity"))["total"] or 0
    
    # Revenue estimate (from subscriptions)
    subscriptions = Subscription.objects.filter(status="active").select_related("tier")
    revenue = sum(
        float(s.tier.price_monthly) if s.tier and s.tier.price_monthly else 0 
        for s in subscriptions
    )
    
    # Tier distribution
    tier_dist = dict(
        Tenant.objects.values("tier")
        .annotate(count=Count("id"))
        .values_list("tier", "count")
    )
    
    # Growth metrics
    prev_period = period_start - timedelta(days=days)
    new_tenants = Tenant.objects.filter(created_at__gte=period_start).count()
    prev_new_tenants = Tenant.objects.filter(
        created_at__gte=prev_period,
        created_at__lt=period_start,
    ).count()
    
    growth = {
        "new_tenants": new_tenants,
        "previous_period_tenants": prev_new_tenants,
        "growth_rate": round((new_tenants - prev_new_tenants) / max(prev_new_tenants, 1) * 100, 2),
    }
    
    return PlatformReportOut(
        generated_at=timezone.now().isoformat(),
        period=f"{days} days",
        total_tenants=tenants["total"],
        active_tenants=tenants["active"],
        total_users=total_users,
        total_api_keys=total_keys,
        total_api_calls=total_calls,
        revenue_estimate=revenue,
        tier_distribution=tier_dist,
        growth_metrics=growth,
    )


@router.get("/platform/tenants", response=List[TenantReportOut])
@require_auth(roles=["super-admin"])
@require_permission(Permission.PLATFORM_MANAGE.value)
def list_tenant_reports(
    request: AuthenticatedRequest,
    status: Optional[str] = None,
    tier: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """
    List tenant reports for platform admins.
    
    🚨 SRE: Platform visibility
    """
    queryset = Tenant.objects.all().order_by("-created_at")
    
    if status:
        queryset = queryset.filter(status=status)
    if tier:
        queryset = queryset.filter(tier=tier)
    
    tenants = queryset[offset:offset + limit]
    
    # Build reports
    reports = []
    for tenant in tenants:
        users = TenantUser.objects.filter(tenant=tenant).count()
        keys = APIKey.objects.filter(tenant=tenant).count()
        
        month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        api_calls = UsageRecord.objects.filter(
            tenant=tenant,
            metric_name="api_call",
            recorded_at__gte=month_start,
        ).aggregate(total=Sum("quantity"))["total"] or 0
        
        last_audit = AuditLog.objects.filter(tenant=tenant).order_by("-timestamp").first()
        
        reports.append(TenantReportOut(
            tenant_id=tenant.id,
            name=tenant.name,
            slug=tenant.slug,
            status=tenant.status,
            tier=str(tenant.tier) if tenant.tier else "free",
            users_count=users,
            api_keys_count=keys,
            api_calls_this_month=api_calls,
            created_at=tenant.created_at.isoformat(),
            last_activity=last_audit.timestamp.isoformat() if last_audit else None,
        ))
    
    return reports


@router.get("/platform/export/tenants")
@require_auth(roles=["super-admin"])
@require_permission(Permission.PLATFORM_MANAGE.value)
def export_all_tenants(
    request: AuthenticatedRequest,
    format: str = "csv",
):
    """
    Export all tenants data.
    
    🛠️ DevOps: Bulk export
    """
    tenants = Tenant.objects.all().order_by("-created_at")[:1000]
    
    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "name", "slug", "status", "tier", "created_at"])
        
        for t in tenants:
            writer.writerow([
                str(t.id),
                t.name,
                t.slug,
                t.status,
                str(t.tier) if t.tier else "",
                t.created_at.isoformat(),
            ])
        
        response = HttpResponse(output.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="all_tenants.csv"'
        return response
    
    from django.http import JsonResponse
    return JsonResponse({
        "tenants": [
            {
                "id": str(t.id),
                "name": t.name,
                "slug": t.slug,
                "status": t.status,
                "tier": str(t.tier) if t.tier else None,
                "created_at": t.created_at.isoformat(),
            }
            for t in tenants
        ]
    })