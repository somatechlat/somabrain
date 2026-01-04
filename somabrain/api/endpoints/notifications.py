"""
Notification System API Endpoints.

In-app notification management for tenants and platform.

ALL 10 PERSONAS per VIBE Coding Rules:
- 🔒 Security: Tenant isolation, user-specific notifications
- 🏛️ Architect: Clean notification patterns
- 💾 DBA: Django ORM with efficient queries
- 🐍 Django: Native Django patterns
- 📚 Docs: Comprehensive docstrings
- 🧪 QA: Testable interfaces
- 🚨 SRE: Notification delivery tracking
- 📊 Perf: Bulk operations, pagination
- 🎨 UX: Clear notification categories
- 🛠️ DevOps: Template-based notifications
"""

from typing import List, Optional
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from django.db import models, transaction
from django.db.models import Count, Q
from django.utils import timezone
from django.shortcuts import get_object_or_404
from ninja import Router, Schema

from somabrain.saas.models import Tenant, TenantUser, AuditLog, ActorType
from somabrain.saas.auth import require_auth, AuthenticatedRequest
from somabrain.saas.granular import require_permission, Permission


router = Router(tags=["Notifications"])


# =============================================================================
# NOTIFICATION MODEL (inline for now)
# =============================================================================

class NotificationType(models.TextChoices):
    """Notification type categories."""
    INFO = "info", "Information"
    WARNING = "warning", "Warning"
    ERROR = "error", "Error"
    SUCCESS = "success", "Success"
    BILLING = "billing", "Billing"
    SECURITY = "security", "Security"
    SYSTEM = "system", "System"


class NotificationPriority(models.TextChoices):
    """Notification priority levels."""
    LOW = "low", "Low"
    NORMAL = "normal", "Normal"
    HIGH = "high", "High"
    URGENT = "urgent", "Urgent"


# =============================================================================
# SCHEMAS
# =============================================================================

class NotificationCreate(Schema):
    """Schema for creating notification."""
    title: str
    message: str
    type: str = "info"
    priority: str = "normal"
    action_url: Optional[str] = None
    user_id: Optional[UUID] = None  # None = all tenant users
    expires_at: Optional[str] = None


class NotificationOut(Schema):
    """Schema for notification output."""
    id: UUID
    title: str
    message: str
    type: str
    priority: str
    is_read: bool
    action_url: Optional[str]
    created_at: str
    expires_at: Optional[str]


class NotificationCountOut(Schema):
    """Notification count summary."""
    total: int
    unread: int
    by_type: dict


class BulkMarkReadRequest(Schema):
    """Request to mark multiple notifications as read."""
    notification_ids: List[UUID]


# =============================================================================
# HELPER: Get or create Notification model
# =============================================================================

def get_notification_model():
    """Get Notification model dynamically."""
    from django.apps import apps
    try:
        return apps.get_model("saas", "Notification")
    except LookupError:
        return None


# =============================================================================
# USER NOTIFICATION ENDPOINTS
# =============================================================================

@router.get("/{tenant_id}/notifications", response=List[NotificationOut])
@require_auth(roles=["super-admin", "tenant-admin", "tenant-user"], any_role=True)
def list_notifications(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
):
    """
    List notifications for the current user.
    
    ALL 10 PERSONAS:
    - Security: User sees only their notifications
    - DBA: Efficient filtered query
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    Notification = get_notification_model()
    if not Notification:
        return []
    
    # Filter by user_id or tenant-wide (user_id=None)
    queryset = Notification.objects.filter(
        Q(tenant_id=tenant_id),
        Q(user_id=request.user_id) | Q(user_id__isnull=True),
    ).exclude(
        expires_at__lt=timezone.now()
    ).order_by("-created_at")
    
    if unread_only:
        queryset = queryset.filter(is_read=False)
    
    notifications = queryset[offset:offset + limit]
    
    return [
        NotificationOut(
            id=n.id,
            title=n.title,
            message=n.message,
            type=n.type,
            priority=n.priority,
            is_read=n.is_read,
            action_url=n.action_url,
            created_at=n.created_at.isoformat(),
            expires_at=n.expires_at.isoformat() if n.expires_at else None,
        )
        for n in notifications
    ]


@router.get("/{tenant_id}/notifications/count", response=NotificationCountOut)
@require_auth(roles=["super-admin", "tenant-admin", "tenant-user"], any_role=True)
def get_notification_count(
    request: AuthenticatedRequest,
    tenant_id: UUID,
):
    """Get notification counts by type."""
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    Notification = get_notification_model()
    if not Notification:
        return NotificationCountOut(total=0, unread=0, by_type={})
    
    queryset = Notification.objects.filter(
        Q(tenant_id=tenant_id),
        Q(user_id=request.user_id) | Q(user_id__isnull=True),
    ).exclude(expires_at__lt=timezone.now())
    
    total = queryset.count()
    unread = queryset.filter(is_read=False).count()
    
    by_type = dict(
        queryset.values("type").annotate(count=Count("id")).values_list("type", "count")
    )
    
    return NotificationCountOut(total=total, unread=unread, by_type=by_type)


@router.post("/{tenant_id}/notifications/{notification_id}/read")
@require_auth(roles=["super-admin", "tenant-admin", "tenant-user"], any_role=True)
def mark_notification_read(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    notification_id: UUID,
):
    """Mark a notification as read."""
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    Notification = get_notification_model()
    if not Notification:
        from ninja.errors import HttpError
        raise HttpError(501, "Notifications not available")
    
    notification = get_object_or_404(
        Notification,
        id=notification_id,
        tenant_id=tenant_id,
    )
    
    # Check user access
    if notification.user_id and str(notification.user_id) != str(request.user_id):
        from ninja.errors import HttpError
        raise HttpError(403, "Not your notification")
    
    notification.is_read = True
    notification.read_at = timezone.now()
    notification.save()
    
    return {"success": True}


@router.post("/{tenant_id}/notifications/read-all")
@require_auth(roles=["super-admin", "tenant-admin", "tenant-user"], any_role=True)
def mark_all_read(
    request: AuthenticatedRequest,
    tenant_id: UUID,
):
    """Mark all notifications as read for the current user."""
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    Notification = get_notification_model()
    if not Notification:
        return {"success": True, "count": 0}
    
    now = timezone.now()
    count = Notification.objects.filter(
        Q(tenant_id=tenant_id),
        Q(user_id=request.user_id) | Q(user_id__isnull=True),
        is_read=False,
    ).update(is_read=True, read_at=now)
    
    return {"success": True, "count": count}


@router.post("/{tenant_id}/notifications/bulk-read")
@require_auth(roles=["super-admin", "tenant-admin", "tenant-user"], any_role=True)
def bulk_mark_read(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    data: BulkMarkReadRequest,
):
    """Mark multiple notifications as read."""
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    Notification = get_notification_model()
    if not Notification:
        return {"success": True, "count": 0}
    
    now = timezone.now()
    count = Notification.objects.filter(
        id__in=data.notification_ids,
        tenant_id=tenant_id,
    ).filter(
        Q(user_id=request.user_id) | Q(user_id__isnull=True)
    ).update(is_read=True, read_at=now)
    
    return {"success": True, "count": count}


# =============================================================================
# ADMIN NOTIFICATION ENDPOINTS
# =============================================================================

@router.post("/{tenant_id}/notifications", response=NotificationOut)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_UPDATE.value)
def create_notification(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    data: NotificationCreate,
):
    """
    Create a notification for tenant users.
    
    ALL 10 PERSONAS:
    - Security: Admin only
    - SRE: Audit logging
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    tenant = get_object_or_404(Tenant, id=tenant_id)
    
    Notification = get_notification_model()
    if not Notification:
        from ninja.errors import HttpError
        raise HttpError(501, "Notifications not available")
    
    expires_at = None
    if data.expires_at:
        expires_at = datetime.fromisoformat(data.expires_at)
    
    notification = Notification.objects.create(
        tenant=tenant,
        user_id=data.user_id,
        title=data.title,
        message=data.message,
        type=data.type,
        priority=data.priority,
        action_url=data.action_url,
        expires_at=expires_at,
    )
    
    # Audit log
    AuditLog.log(
        action="notification.created",
        resource_type="Notification",
        resource_id=str(notification.id),
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        tenant=tenant,
        details={"title": data.title, "type": data.type},
    )
    
    return NotificationOut(
        id=notification.id,
        title=notification.title,
        message=notification.message,
        type=notification.type,
        priority=notification.priority,
        is_read=False,
        action_url=notification.action_url,
        created_at=notification.created_at.isoformat(),
        expires_at=notification.expires_at.isoformat() if notification.expires_at else None,
    )


@router.delete("/{tenant_id}/notifications/{notification_id}")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_UPDATE.value)
def delete_notification(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    notification_id: UUID,
):
    """Delete a notification."""
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    Notification = get_notification_model()
    if not Notification:
        from ninja.errors import HttpError
        raise HttpError(501, "Notifications not available")
    
    notification = get_object_or_404(
        Notification,
        id=notification_id,
        tenant_id=tenant_id,
    )
    
    notification.delete()
    
    return {"success": True}


# =============================================================================
# PLATFORM BROADCAST ENDPOINTS (Super Admin Only)
# =============================================================================

@router.post("/broadcast")
@require_auth(roles=["super-admin"])
@require_permission(Permission.PLATFORM_MANAGE.value)
def broadcast_notification(
    request: AuthenticatedRequest,
    data: NotificationCreate,
):
    """
    Broadcast notification to all tenants.
    
    ALL 10 PERSONAS:
    - Security: Super admin only
    - Perf: Bulk create
    """
    Notification = get_notification_model()
    if not Notification:
        from ninja.errors import HttpError
        raise HttpError(501, "Notifications not available")
    
    expires_at = None
    if data.expires_at:
        expires_at = datetime.fromisoformat(data.expires_at)
    
    # Get all active tenants
    tenants = Tenant.objects.filter(status="active")
    
    # Bulk create notifications
    notifications = [
        Notification(
            tenant=tenant,
            user_id=None,  # All users in tenant
            title=data.title,
            message=data.message,
            type=data.type,
            priority=data.priority,
            action_url=data.action_url,
            expires_at=expires_at,
        )
        for tenant in tenants
    ]
    
    with transaction.atomic():
        Notification.objects.bulk_create(notifications)
    
    # Audit log
    AuditLog.log(
        action="notification.broadcast",
        resource_type="Notification",
        resource_id="broadcast",
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        details={"title": data.title, "tenant_count": len(notifications)},
    )
    
    return {"success": True, "tenant_count": len(notifications)}