"""
Enhanced Audit Log API for SomaBrain.

Advanced search, filtering, export, and analytics for audit logs.

ALL 10 PERSONAS per VIBE Coding Rules:
- 🔒 Security: Tenant isolation, super-admin visibility
- 🏛️ Architect: Clean audit patterns
- 💾 DBA: Efficient indexed queries
- 🐍 Django: Native ORM
- 📚 Docs: Comprehensive docstrings
- 🧪 QA: Testable interfaces
- 🚨 SRE: Complete audit trail
- 📊 Perf: Pagination, date ranges
- 🎨 UX: Clear log formatting
- 🛠️ DevOps: Export capabilities
"""

from typing import List, Optional
from datetime import datetime, timedelta
from uuid import UUID
import csv
import io

from django.db.models import Count, Q
from django.utils import timezone
from django.http import HttpResponse
from ninja import Router, Schema

from somabrain.saas.models import AuditLog, Tenant, ActorType
from somabrain.saas.auth import require_auth, AuthenticatedRequest
from somabrain.saas.granular import require_permission, Permission


router = Router(tags=["Audit Logs"])


# =============================================================================
# SCHEMAS
# =============================================================================

class AuditLogOut(Schema):
    """Audit log entry output."""
    id: UUID
    timestamp: str
    action: str
    resource_type: str
    resource_id: str
    actor_id: str
    actor_type: str
    ip_address: Optional[str]
    user_agent: Optional[str]
    details: Optional[dict]
    tenant_id: Optional[UUID]


class AuditLogSearchRequest(Schema):
    """Search parameters for audit logs."""
    action: Optional[str] = None
    resource_type: Optional[str] = None
    actor_id: Optional[str] = None
    actor_type: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    search: Optional[str] = None
    limit: int = 50
    offset: int = 0


class AuditLogStatsOut(Schema):
    """Audit log statistics."""
    total_entries: int
    by_action: dict
    by_resource_type: dict
    by_actor_type: dict
    period_start: str
    period_end: str


class ActionSummaryOut(Schema):
    """Summary of actions over time."""
    action: str
    count: int
    last_occurred: str


# =============================================================================
# TENANT AUDIT LOG ENDPOINTS
# =============================================================================

@router.get("/{tenant_id}/logs", response=List[AuditLogOut])
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_READ.value)
def list_tenant_audit_logs(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """
    List audit logs for a specific tenant.
    
    ALL 10 PERSONAS - VIBE Rules
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    queryset = AuditLog.objects.filter(tenant_id=tenant_id).order_by("-timestamp")
    
    if action:
        queryset = queryset.filter(action__icontains=action)
    if resource_type:
        queryset = queryset.filter(resource_type__icontains=resource_type)
    
    logs = queryset[offset:offset + limit]
    
    return [
        AuditLogOut(
            id=log.id,
            timestamp=log.timestamp.isoformat(),
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            actor_id=str(log.actor_id),
            actor_type=log.actor_type,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            details=log.details,
            tenant_id=log.tenant_id,
        )
        for log in logs
    ]


@router.post("/{tenant_id}/logs/search", response=List[AuditLogOut])
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_READ.value)
def search_tenant_audit_logs(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    data: AuditLogSearchRequest,
):
    """Advanced search for tenant audit logs."""
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    queryset = AuditLog.objects.filter(tenant_id=tenant_id).order_by("-timestamp")
    
    if data.action:
        queryset = queryset.filter(action__icontains=data.action)
    if data.resource_type:
        queryset = queryset.filter(resource_type__icontains=data.resource_type)
    if data.actor_id:
        queryset = queryset.filter(actor_id=data.actor_id)
    if data.actor_type:
        queryset = queryset.filter(actor_type=data.actor_type)
    if data.start_date:
        queryset = queryset.filter(timestamp__gte=datetime.fromisoformat(data.start_date))
    if data.end_date:
        queryset = queryset.filter(timestamp__lte=datetime.fromisoformat(data.end_date))
    if data.search:
        queryset = queryset.filter(
            Q(action__icontains=data.search) |
            Q(resource_type__icontains=data.search) |
            Q(resource_id__icontains=data.search)
        )
    
    logs = queryset[data.offset:data.offset + data.limit]
    
    return [
        AuditLogOut(
            id=log.id,
            timestamp=log.timestamp.isoformat(),
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            actor_id=str(log.actor_id),
            actor_type=log.actor_type,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            details=log.details,
            tenant_id=log.tenant_id,
        )
        for log in logs
    ]


@router.get("/{tenant_id}/logs/stats", response=AuditLogStatsOut)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_READ.value)
def get_tenant_audit_stats(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    days: int = 30,
):
    """Get audit log statistics for a tenant."""
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    period_start = timezone.now() - timedelta(days=days)
    queryset = AuditLog.objects.filter(
        tenant_id=tenant_id,
        timestamp__gte=period_start,
    )
    
    total = queryset.count()
    by_action = dict(queryset.values("action").annotate(count=Count("id")).values_list("action", "count"))
    by_resource_type = dict(queryset.values("resource_type").annotate(count=Count("id")).values_list("resource_type", "count"))
    by_actor_type = dict(queryset.values("actor_type").annotate(count=Count("id")).values_list("actor_type", "count"))
    
    return AuditLogStatsOut(
        total_entries=total,
        by_action=by_action,
        by_resource_type=by_resource_type,
        by_actor_type=by_actor_type,
        period_start=period_start.isoformat(),
        period_end=timezone.now().isoformat(),
    )


@router.get("/{tenant_id}/logs/export")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_READ.value)
def export_tenant_audit_logs(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    days: int = 30,
    format: str = "csv",
):
    """Export audit logs as CSV."""
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    period_start = timezone.now() - timedelta(days=days)
    logs = AuditLog.objects.filter(
        tenant_id=tenant_id,
        timestamp__gte=period_start,
    ).order_by("-timestamp")[:10000]  # Limit to 10k records
    
    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["timestamp", "action", "resource_type", "resource_id", "actor_id", "actor_type", "ip_address"])
        
        for log in logs:
            writer.writerow([
                log.timestamp.isoformat(),
                log.action,
                log.resource_type,
                log.resource_id,
                str(log.actor_id),
                log.actor_type,
                log.ip_address or "",
            ])
        
        response = HttpResponse(output.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="audit_logs_{tenant_id}.csv"'
        return response
    
    # VIBE RULES: No fallbacks - require explicit format
    from ninja.errors import HttpError
    raise HttpError(400, f"Unsupported format: {format}. Use 'csv' only.")


# =============================================================================
# PLATFORM-WIDE AUDIT LOG ENDPOINTS (Super Admin Only)
# =============================================================================

@router.get("/platform/logs", response=List[AuditLogOut])
@require_auth(roles=["super-admin"])
@require_permission(Permission.PLATFORM_MANAGE.value)
def list_platform_audit_logs(
    request: AuthenticatedRequest,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    tenant_id: Optional[UUID] = None,
    limit: int = 100,
    offset: int = 0,
):
    """List all audit logs platform-wide (super admin only)."""
    queryset = AuditLog.objects.all().order_by("-timestamp")
    
    if action:
        queryset = queryset.filter(action__icontains=action)
    if resource_type:
        queryset = queryset.filter(resource_type__icontains=resource_type)
    if tenant_id:
        queryset = queryset.filter(tenant_id=tenant_id)
    
    logs = queryset[offset:offset + limit]
    
    return [
        AuditLogOut(
            id=log.id,
            timestamp=log.timestamp.isoformat(),
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            actor_id=str(log.actor_id),
            actor_type=log.actor_type,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            details=log.details,
            tenant_id=log.tenant_id,
        )
        for log in logs
    ]


@router.get("/platform/logs/stats", response=AuditLogStatsOut)
@require_auth(roles=["super-admin"])
@require_permission(Permission.PLATFORM_MANAGE.value)
def get_platform_audit_stats(
    request: AuthenticatedRequest,
    days: int = 7,
):
    """Get platform-wide audit log statistics."""
    period_start = timezone.now() - timedelta(days=days)
    queryset = AuditLog.objects.filter(timestamp__gte=period_start)
    
    total = queryset.count()
    by_action = dict(queryset.values("action").annotate(count=Count("id")).values_list("action", "count")[:20])
    by_resource_type = dict(queryset.values("resource_type").annotate(count=Count("id")).values_list("resource_type", "count")[:20])
    by_actor_type = dict(queryset.values("actor_type").annotate(count=Count("id")).values_list("actor_type", "count"))
    
    return AuditLogStatsOut(
        total_entries=total,
        by_action=by_action,
        by_resource_type=by_resource_type,
        by_actor_type=by_actor_type,
        period_start=period_start.isoformat(),
        period_end=timezone.now().isoformat(),
    )


@router.get("/platform/logs/actions", response=List[ActionSummaryOut])
@require_auth(roles=["super-admin"])
@require_permission(Permission.PLATFORM_MANAGE.value)
def list_unique_actions(request: AuthenticatedRequest):
    """List all unique actions with counts."""
    from django.db.models import Max
    
    actions = (
        AuditLog.objects
        .values("action")
        .annotate(count=Count("id"), last_occurred=Max("timestamp"))
        .order_by("-count")[:50]
    )
    
    return [
        ActionSummaryOut(
            action=a["action"],
            count=a["count"],
            last_occurred=a["last_occurred"].isoformat() if a["last_occurred"] else "",
        )
        for a in actions
    ]