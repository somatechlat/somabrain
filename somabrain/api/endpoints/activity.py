"""
Activity Timeline and Event Tracking API for SomaBrain.

Track and display user activities in a timeline format.

ALL 10 PERSONAS - VIBE Coding Rules:
- 🔒 Security: Tenant-scoped activity tracking
- 🏛️ Architect: Clean event sourcing patterns
- 💾 DBA: Django ORM with efficient time queries
- 🐍 Django Expert: Native Django patterns
- 📚 Technical Writer: Comprehensive docstrings
- 🧪 QA Engineer: Testable activity records
- 🚨 SRE: Activity monitoring and alerts
- 📊 Performance: Paginated timeline queries
- 🎨 UX: Grouped timeline view
- 🛠️ DevOps: Activity retention policies
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from enum import Enum

from django.utils import timezone
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from ninja import Router, Schema

from somabrain.saas.models import (
    Tenant, TenantUser, AuditLog, ActorType
)
from somabrain.saas.auth import require_auth, AuthenticatedRequest
from somabrain.saas.granular import require_permission, Permission


router = Router(tags=["Activity"])


# =============================================================================
# ACTIVITY TYPES - ALL 10 PERSONAS
# =============================================================================

class ActivityType(str, Enum):
    """Activity types for the timeline."""
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    API_KEY_CREATED = "api_key.created"
    API_KEY_USED = "api_key.used"
    API_KEY_REVOKED = "api_key.revoked"
    MEMORY_CREATED = "memory.created"
    MEMORY_QUERIED = "memory.queried"
    WEBHOOK_TRIGGERED = "webhook.triggered"
    SETTINGS_UPDATED = "settings.updated"
    SUBSCRIPTION_CHANGED = "subscription.changed"
    INVITATION_SENT = "invitation.sent"
    INVITATION_ACCEPTED = "invitation.accepted"


# =============================================================================
# ACTIVITY STORAGE (Cache-backed for recent activities)
# =============================================================================

def get_activities_key(tenant_id: str) -> str:
    """Retrieve activities key.

        Args:
            tenant_id: The tenant_id.
        """

    return f"activities:tenant:{tenant_id}"


def get_user_activities_key(user_id: str) -> str:
    """Retrieve user activities key.

        Args:
            user_id: The user_id.
        """

    return f"activities:user:{user_id}"


def record_activity(
    tenant_id: str,
    user_id: str,
    activity_type: str,
    description: str,
    metadata: Optional[Dict] = None,
):
    """Record a new activity."""
    activity = {
        "id": str(uuid4()),
        "tenant_id": tenant_id,
        "user_id": user_id,
        "type": activity_type,
        "description": description,
        "metadata": metadata or {},
        "timestamp": timezone.now().isoformat(),
    }
    
    # Store in tenant activities (limited to 500 recent)
    tenant_key = get_activities_key(tenant_id)
    activities = cache.get(tenant_key, [])
    activities.insert(0, activity)
    activities = activities[:500]
    cache.set(tenant_key, activities, timeout=86400 * 7)
    
    # Store in user activities (limited to 100 recent)
    user_key = get_user_activities_key(user_id)
    user_activities = cache.get(user_key, [])
    user_activities.insert(0, activity)
    user_activities = user_activities[:100]
    cache.set(user_key, user_activities, timeout=86400 * 7)
    
    return activity


def get_tenant_activities(tenant_id: str, limit: int = 50) -> List[dict]:
    """Get recent tenant activities."""
    key = get_activities_key(tenant_id)
    activities = cache.get(key, [])
    return activities[:limit]


def get_user_activities(user_id: str, limit: int = 50) -> List[dict]:
    """Get recent user activities."""
    key = get_user_activities_key(user_id)
    activities = cache.get(key, [])
    return activities[:limit]


# =============================================================================
# SCHEMAS - ALL 10 PERSONAS
# =============================================================================

class ActivityOut(Schema):
    """Activity output."""
    id: str
    type: str
    description: str
    user_id: Optional[str]
    metadata: Optional[Dict[str, Any]]
    timestamp: str


class TimelineGroup(Schema):
    """Grouped timeline activities."""
    date: str
    activities: List[ActivityOut]


class ActivityRecord(Schema):
    """Record a new activity."""
    type: str
    description: str
    metadata: Optional[Dict[str, Any]] = None


class ActivityStats(Schema):
    """Activity statistics."""
    total_activities: int
    activities_today: int
    activities_this_week: int
    top_activity_types: Dict[str, int]
    most_active_users: List[Dict[str, Any]]


# =============================================================================
# ACTIVITY ENDPOINTS - ALL 10 PERSONAS
# =============================================================================

@router.get("/{tenant_id}/timeline", response=List[ActivityOut])
@require_auth(roles=["super-admin", "tenant-admin", "tenant-user"], any_role=True)
def get_timeline(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    limit: int = 50,
    activity_type: Optional[str] = None,
    user_id: Optional[str] = None,
):
    """
    Get activity timeline for a tenant.
    
    📊 Performance: Paginated results
    🎨 UX: Filterable timeline
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    activities = get_tenant_activities(str(tenant_id), limit * 2)
    
    # Filter by type
    if activity_type:
        activities = [a for a in activities if a["type"] == activity_type]
    
    # Filter by user
    if user_id:
        activities = [a for a in activities if a["user_id"] == user_id]
    
    # Apply limit
    activities = activities[:limit]
    
    return [
        ActivityOut(
            id=a["id"],
            type=a["type"],
            description=a["description"],
            user_id=a.get("user_id"),
            metadata=a.get("metadata"),
            timestamp=a["timestamp"],
        )
        for a in activities
    ]


@router.get("/{tenant_id}/timeline/grouped", response=List[TimelineGroup])
@require_auth(roles=["super-admin", "tenant-admin", "tenant-user"], any_role=True)
def get_grouped_timeline(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    days: int = 7,
):
    """
    Get activity timeline grouped by date.
    
    🎨 UX: Date-grouped view
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    activities = get_tenant_activities(str(tenant_id), 200)
    
    # Group by date
    grouped = {}
    cutoff = timezone.now() - timedelta(days=days)
    
    for activity in activities:
        ts = datetime.fromisoformat(activity["timestamp"])
        if ts < cutoff:
            continue
        
        date_key = ts.strftime("%Y-%m-%d")
        if date_key not in grouped:
            grouped[date_key] = []
        
        grouped[date_key].append(ActivityOut(
            id=activity["id"],
            type=activity["type"],
            description=activity["description"],
            user_id=activity.get("user_id"),
            metadata=activity.get("metadata"),
            timestamp=activity["timestamp"],
        ))
    
    # Sort by date descending
    result = [
        TimelineGroup(date=date, activities=acts)
        for date, acts in sorted(grouped.items(), reverse=True)
    ]
    
    return result


@router.get("/{tenant_id}/user/{user_id}", response=List[ActivityOut])
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
def get_user_timeline(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    user_id: UUID,
    limit: int = 50,
):
    """
    Get activity timeline for a specific user.
    
    🔒 Security: Admin only for user history
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    # Verify user belongs to tenant
    user = get_object_or_404(TenantUser, id=user_id, tenant_id=tenant_id)
    
    activities = get_user_activities(str(user_id), limit)
    
    return [
        ActivityOut(
            id=a["id"],
            type=a["type"],
            description=a["description"],
            user_id=a.get("user_id"),
            metadata=a.get("metadata"),
            timestamp=a["timestamp"],
        )
        for a in activities
    ]


@router.post("/{tenant_id}/record", response=ActivityOut)
@require_auth(roles=["super-admin", "tenant-admin", "tenant-user"], any_role=True)
def record_user_activity(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    data: ActivityRecord,
):
    """
    Record a new activity.
    
    🚨 SRE: Activity tracking
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    activity = record_activity(
        tenant_id=str(tenant_id),
        user_id=str(request.user_id),
        activity_type=data.type,
        description=data.description,
        metadata=data.metadata,
    )
    
    return ActivityOut(
        id=activity["id"],
        type=activity["type"],
        description=activity["description"],
        user_id=activity["user_id"],
        metadata=activity.get("metadata"),
        timestamp=activity["timestamp"],
    )


@router.get("/{tenant_id}/stats", response=ActivityStats)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
def get_activity_stats(
    request: AuthenticatedRequest,
    tenant_id: UUID,
):
    """
    Get activity statistics for a tenant.
    
    📊 Performance: Analytics
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    activities = get_tenant_activities(str(tenant_id), 500)
    
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    
    activities_today = 0
    activities_week = 0
    type_counts = {}
    user_counts = {}
    
    for activity in activities:
        ts = datetime.fromisoformat(activity["timestamp"])
        
        if ts >= today_start:
            activities_today += 1
        if ts >= week_start:
            activities_week += 1
        
        # Count by type
        atype = activity["type"]
        type_counts[atype] = type_counts.get(atype, 0) + 1
        
        # Count by user
        uid = activity.get("user_id", "unknown")
        user_counts[uid] = user_counts.get(uid, 0) + 1
    
    # Sort and limit
    top_types = dict(sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:10])
    top_users = [
        {"user_id": uid, "count": count}
        for uid, count in sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    ]
    
    return ActivityStats(
        total_activities=len(activities),
        activities_today=activities_today,
        activities_this_week=activities_week,
        top_activity_types=top_types,
        most_active_users=top_users,
    )


# =============================================================================
# AUDIT LOG INTEGRATION
# =============================================================================

@router.get("/{tenant_id}/audit-feed", response=List[ActivityOut])
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_READ.value)
def get_audit_feed(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    limit: int = 50,
):
    """
    Get audit log entries as activity feed.
    
    🚨 SRE: Audit integration
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    logs = AuditLog.objects.filter(
        tenant_id=tenant_id
    ).order_by("-timestamp")[:limit]
    
    return [
        ActivityOut(
            id=str(log.id),
            type=log.action,
            description=f"{log.action} on {log.resource_type} ({log.resource_id})",
            user_id=log.actor_id,
            metadata={"resource_type": log.resource_type, "resource_id": log.resource_id},
            timestamp=log.timestamp.isoformat(),
        )
        for log in logs
    ]


@router.get("/{tenant_id}/realtime/recent")
@require_auth(roles=["super-admin", "tenant-admin", "tenant-user"], any_role=True)
def get_recent_activity(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    since_minutes: int = 5,
):
    """
    Get very recent activities for realtime updates.
    
    📊 Performance: Short window polling
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    activities = get_tenant_activities(str(tenant_id), 100)
    cutoff = timezone.now() - timedelta(minutes=since_minutes)
    
    recent = [
        a for a in activities
        if datetime.fromisoformat(a["timestamp"]) >= cutoff
    ]
    
    return {
        "since": cutoff.isoformat(),
        "count": len(recent),
        "activities": recent,
    }