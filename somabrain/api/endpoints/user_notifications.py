"""
Notifications API for SomaBrain.

User notifications with real Django cache storage.
Uses REAL Django cache - NO mocks, NO fallbacks.

ALL 10 PERSONAS - VIBE Coding Rules:
- 🔒 Security: User-scoped notifications
- 🏛️ Architect: Clean notification patterns
- 💾 DBA: Real Django cache storage
- 🐍 Django Expert: Native Django patterns
- 📚 Technical Writer: Notification docs
- 🧪 QA Engineer: Notification validation
- 🚨 SRE: Alert notifications
- 📊 Performance: Real-time updates
- 🎨 UX: Clear notification UI
- 🛠️ DevOps: Notification delivery
"""

from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from django.core.cache import cache
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router, Schema
from ninja.errors import HttpError

from somabrain.aaas.auth import AuthenticatedRequest, require_auth
from somabrain.aaas.granular import Permission, require_permission
from somabrain.aaas.models import (
    ActorType,
    AuditLog,
    Tenant,
    TenantUser,
)

router = Router(tags=["Notifications"])


# =============================================================================
# NOTIFICATION TYPES
# =============================================================================


class NotificationType(str, Enum):
    """Notificationtype class implementation."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"
    ALERT = "alert"
    SYSTEM = "system"


class NotificationPriority(str, Enum):
    """Notificationpriority class implementation."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


# =============================================================================
# NOTIFICATION STORAGE (Real Django Cache)
# =============================================================================


def get_notifications_key(user_id: str) -> str:
    """Retrieve notifications key.

    Args:
        user_id: The user_id.
    """

    return f"notifications:user:{user_id}"


def get_notification_key(notification_id: str) -> str:
    """Retrieve notification key.

    Args:
        notification_id: The notification_id.
    """

    return f"notification:{notification_id}"


def create_notification(
    user_id: str,
    tenant_id: str,
    title: str,
    message: str,
    notification_type: str = "info",
    priority: str = "normal",
    action_url: Optional[str] = None,
) -> dict:
    """Create REAL notification in Django cache."""
    notification_id = str(uuid4())

    notification = {
        "id": notification_id,
        "user_id": user_id,
        "tenant_id": tenant_id,
        "title": title,
        "message": message,
        "type": notification_type,
        "priority": priority,
        "action_url": action_url,
        "is_read": False,
        "created_at": timezone.now().isoformat(),
        "read_at": None,
    }

    # Store in REAL Django cache
    cache.set(get_notification_key(notification_id), notification, timeout=86400 * 7)

    # Add to user's notification list
    user_notifications = cache.get(get_notifications_key(user_id), [])
    user_notifications.insert(0, notification_id)  # Newest first
    user_notifications = user_notifications[:100]  # Keep last 100
    cache.set(get_notifications_key(user_id), user_notifications, timeout=86400 * 7)

    return notification


def get_user_notifications(user_id: str, unread_only: bool = False) -> List[dict]:
    """Get notifications from REAL Django cache."""
    notification_ids = cache.get(get_notifications_key(user_id), [])
    notifications = []

    for nid in notification_ids:
        notification = cache.get(get_notification_key(nid))
        if notification:
            if unread_only and notification.get("is_read"):
                continue
            notifications.append(notification)

    return notifications


def mark_notification_read(notification_id: str) -> bool:
    """Mark notification as read in REAL cache."""
    notification = cache.get(get_notification_key(notification_id))
    if notification:
        notification["is_read"] = True
        notification["read_at"] = timezone.now().isoformat()
        cache.set(
            get_notification_key(notification_id), notification, timeout=86400 * 7
        )
        return True
    return False


# =============================================================================
# SCHEMAS
# =============================================================================


class NotificationOut(Schema):
    """Notification output."""

    id: str
    title: str
    message: str
    type: str
    priority: str
    action_url: Optional[str]
    is_read: bool
    created_at: str
    read_at: Optional[str]


class NotificationCreate(Schema):
    """Create notification input."""

    title: str
    message: str
    type: str = "info"
    priority: str = "normal"
    action_url: Optional[str] = None


class NotificationStats(Schema):
    """Notification statistics."""

    total: int
    unread: int
    by_type: dict
    by_priority: dict


# =============================================================================
# USER ENDPOINTS
# =============================================================================


@router.get("/{tenant_id}/notifications", response=List[NotificationOut])
@require_auth(roles=["super-admin", "tenant-admin", "tenant-user"], any_role=True)
def list_notifications(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    unread_only: bool = False,
    limit: int = 50,
):
    """
    List current user's notifications.

    🎨 UX: Notification inbox

    REAL data from Django cache.
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            raise HttpError(403, "Access denied")

    notifications = get_user_notifications(str(request.user_id), unread_only)

    return [
        NotificationOut(
            id=n["id"],
            title=n.get("title", ""),
            message=n.get("message", ""),
            type=n.get("type", "info"),
            priority=n.get("priority", "normal"),
            action_url=n.get("action_url"),
            is_read=n.get("is_read", False),
            created_at=n.get("created_at", ""),
            read_at=n.get("read_at"),
        )
        for n in notifications[:limit]
    ]


@router.get("/{tenant_id}/notifications/unread-count")
@require_auth(roles=["super-admin", "tenant-admin", "tenant-user"], any_role=True)
def get_unread_count(
    request: AuthenticatedRequest,
    tenant_id: UUID,
):
    """Get unread notification count."""
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            raise HttpError(403, "Access denied")

    notifications = get_user_notifications(str(request.user_id), unread_only=True)

    return {"unread_count": len(notifications)}


@router.get("/{tenant_id}/notifications/{notification_id}", response=NotificationOut)
@require_auth(roles=["super-admin", "tenant-admin", "tenant-user"], any_role=True)
def get_notification(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    notification_id: str,
):
    """Get a specific notification."""
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            raise HttpError(403, "Access denied")

    notification = cache.get(get_notification_key(notification_id))
    if not notification:
        raise HttpError(404, "Notification not found")

    # User can only see their own notifications
    if (
        notification.get("user_id") != str(request.user_id)
        and not request.is_super_admin
    ):
        raise HttpError(403, "Access denied")

    return NotificationOut(
        id=notification["id"],
        title=notification.get("title", ""),
        message=notification.get("message", ""),
        type=notification.get("type", "info"),
        priority=notification.get("priority", "normal"),
        action_url=notification.get("action_url"),
        is_read=notification.get("is_read", False),
        created_at=notification.get("created_at", ""),
        read_at=notification.get("read_at"),
    )


@router.post("/{tenant_id}/notifications/{notification_id}/read")
@require_auth(roles=["super-admin", "tenant-admin", "tenant-user"], any_role=True)
def mark_as_read(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    notification_id: str,
):
    """Mark notification as read."""
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            raise HttpError(403, "Access denied")

    notification = cache.get(get_notification_key(notification_id))
    if not notification:
        raise HttpError(404, "Notification not found")

    if (
        notification.get("user_id") != str(request.user_id)
        and not request.is_super_admin
    ):
        raise HttpError(403, "Access denied")

    success = mark_notification_read(notification_id)

    return {"success": success}


@router.post("/{tenant_id}/notifications/mark-all-read")
@require_auth(roles=["super-admin", "tenant-admin", "tenant-user"], any_role=True)
def mark_all_as_read(
    request: AuthenticatedRequest,
    tenant_id: UUID,
):
    """Mark all notifications as read."""
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            raise HttpError(403, "Access denied")

    notifications = get_user_notifications(str(request.user_id), unread_only=True)
    count = 0

    for n in notifications:
        if mark_notification_read(n["id"]):
            count += 1

    return {"marked_count": count}


@router.delete("/{tenant_id}/notifications/{notification_id}")
@require_auth(roles=["super-admin", "tenant-admin", "tenant-user"], any_role=True)
def delete_notification(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    notification_id: str,
):
    """Delete a notification."""
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            raise HttpError(403, "Access denied")

    notification = cache.get(get_notification_key(notification_id))
    if not notification:
        raise HttpError(404, "Notification not found")

    if (
        notification.get("user_id") != str(request.user_id)
        and not request.is_super_admin
    ):
        raise HttpError(403, "Access denied")

    # Delete from cache
    cache.delete(get_notification_key(notification_id))

    # Remove from user's list
    user_notifications = cache.get(get_notifications_key(str(request.user_id)), [])
    if notification_id in user_notifications:
        user_notifications.remove(notification_id)
        cache.set(
            get_notifications_key(str(request.user_id)),
            user_notifications,
            timeout=86400 * 7,
        )

    return {"deleted": True}


# =============================================================================
# ADMIN ENDPOINTS
# =============================================================================


@router.post("/{tenant_id}/admin/notifications/send")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.USERS_UPDATE.value)
def send_notification(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    user_id: str,
    data: NotificationCreate,
):
    """
    Send notification to a user (admin).

    🛠️ DevOps: Admin notifications

    REAL cache storage.
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            raise HttpError(403, "Access denied")

    # Verify user exists - REAL check
    user = get_object_or_404(TenantUser, id=user_id, tenant_id=tenant_id)

    notification = create_notification(
        user_id=str(user.id),
        tenant_id=str(tenant_id),
        title=data.title,
        message=data.message,
        notification_type=data.type,
        priority=data.priority,
        action_url=data.action_url,
    )

    # Audit log - REAL
    tenant = get_object_or_404(Tenant, id=tenant_id)
    AuditLog.log(
        action="notification.sent",
        resource_type="Notification",
        resource_id=notification["id"],
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        tenant=tenant,
        details={"recipient": str(user.id), "title": data.title},
    )

    return {"success": True, "notification_id": notification["id"]}


@router.post("/{tenant_id}/admin/notifications/broadcast")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.USERS_UPDATE.value)
def broadcast_notification(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    data: NotificationCreate,
):
    """
    Broadcast notification to all tenant users.

    🚨 SRE: System announcements

    REAL broadcast to all users.
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            raise HttpError(403, "Access denied")

    # Get all REAL users in tenant
    users = TenantUser.objects.filter(tenant_id=tenant_id, is_active=True)

    sent_count = 0
    for user in users[:100]:  # Limit to 100 users
        create_notification(
            user_id=str(user.id),
            tenant_id=str(tenant_id),
            title=data.title,
            message=data.message,
            notification_type=data.type,
            priority=data.priority,
            action_url=data.action_url,
        )
        sent_count += 1

    # Audit log - REAL
    tenant = get_object_or_404(Tenant, id=tenant_id)
    AuditLog.log(
        action="notification.broadcast",
        resource_type="Tenant",
        resource_id=str(tenant.id),
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        tenant=tenant,
        details={"title": data.title, "sent_count": sent_count},
    )

    return {"success": True, "sent_count": sent_count}


@router.get("/{tenant_id}/admin/notifications/stats", response=NotificationStats)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
def get_notification_stats(
    request: AuthenticatedRequest,
    tenant_id: UUID,
):
    """
    Get notification statistics for tenant.

    📊 Performance: REAL aggregated stats
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            raise HttpError(403, "Access denied")

    # Get all REAL users in tenant
    users = TenantUser.objects.filter(tenant_id=tenant_id, is_active=True)[:50]

    total = 0
    unread = 0
    by_type = {}
    by_priority = {}

    for user in users:
        notifications = get_user_notifications(str(user.id))
        for n in notifications:
            total += 1
            if not n.get("is_read"):
                unread += 1

            n_type = n.get("type", "info")
            by_type[n_type] = by_type.get(n_type, 0) + 1

            n_priority = n.get("priority", "normal")
            by_priority[n_priority] = by_priority.get(n_priority, 0) + 1

    return NotificationStats(
        total=total,
        unread=unread,
        by_type=by_type,
        by_priority=by_priority,
    )
