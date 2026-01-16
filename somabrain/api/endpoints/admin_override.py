"""
Admin Override API for SomaBrain.

Super admin override capabilities with real Django ORM.
Uses REAL Django ORM - NO mocks, NO fallbacks.

ALL 10 PERSONAS - VIBE Coding Rules:
- 🔒 Security: Super admin only
- 🏛️ Architect: Clean override patterns
- 💾 DBA: Real Django ORM operations
- 🐍 Django Expert: Native Django patterns
- 📚 Technical Writer: Override documentation
- 🧪 QA Engineer: Override validation
- 🚨 SRE: Override auditing
- 📊 Performance: Efficient operations
- 🎨 UX: Clear override feedback
- 🛠️ DevOps: System maintenance
"""

from typing import List, Optional
from uuid import UUID

from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.db import transaction
from ninja import Router, Schema
from ninja.errors import HttpError

from somabrain.saas.models import (
    Tenant,
    TenantUser,
    SubscriptionTier,
    APIKey,
    AuditLog,
    ActorType,
    TenantStatus,
)
from somabrain.saas.auth import require_auth, AuthenticatedRequest
from somabrain.saas.granular import require_permission, Permission


router = Router(tags=["Admin Override"])


# =============================================================================
# SCHEMAS
# =============================================================================


class OverrideResult(Schema):
    """Override operation result."""

    success: bool
    action: str
    target_id: str
    target_type: str
    details: dict
    timestamp: str


class TenantOverride(Schema):
    """Tenant override data."""

    tenant_id: str
    tenant_name: str
    status: str
    tier: str
    user_count: int
    created_at: str


class MaintenanceMode(Schema):
    """Maintenance mode status."""

    enabled: bool
    message: str
    started_at: Optional[str]
    expected_end: Optional[str]


# =============================================================================
# TENANT OVERRIDE ENDPOINTS
# =============================================================================


@router.post("/tenant/{tenant_id}/suspend")
@require_auth(roles=["super-admin"])
@require_permission(Permission.PLATFORM_MANAGE.value)
def suspend_tenant(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    reason: str = "Admin suspension",
):
    """
    Suspend a tenant (super admin).

    🔒 Security: Super admin only

    REAL database update.
    """
    tenant = get_object_or_404(Tenant, id=tenant_id)

    # REAL suspension
    old_status = tenant.status
    tenant.status = TenantStatus.SUSPENDED
    tenant.suspension_reason = reason
    tenant.save(update_fields=["status", "suspension_reason", "updated_at"])

    # Audit log - REAL
    AuditLog.log(
        action="admin.tenant_suspended",
        resource_type="Tenant",
        resource_id=str(tenant.id),
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        tenant=tenant,
        details={"old_status": old_status, "reason": reason},
    )

    return OverrideResult(
        success=True,
        action="suspend",
        target_id=str(tenant.id),
        target_type="Tenant",
        details={"old_status": old_status, "new_status": "suspended"},
        timestamp=timezone.now().isoformat(),
    )


@router.post("/tenant/{tenant_id}/activate")
@require_auth(roles=["super-admin"])
@require_permission(Permission.PLATFORM_MANAGE.value)
def activate_tenant(
    request: AuthenticatedRequest,
    tenant_id: UUID,
):
    """
    Activate a suspended tenant.

    REAL database update.
    """
    tenant = get_object_or_404(Tenant, id=tenant_id)

    old_status = tenant.status
    tenant.status = TenantStatus.ACTIVE
    tenant.suspension_reason = None
    tenant.save(update_fields=["status", "suspension_reason", "updated_at"])

    # Audit log - REAL
    AuditLog.log(
        action="admin.tenant_activated",
        resource_type="Tenant",
        resource_id=str(tenant.id),
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        tenant=tenant,
        details={"old_status": old_status},
    )

    return OverrideResult(
        success=True,
        action="activate",
        target_id=str(tenant.id),
        target_type="Tenant",
        details={"old_status": old_status, "new_status": "active"},
        timestamp=timezone.now().isoformat(),
    )


@router.post("/tenant/{tenant_id}/change-tier")
@require_auth(roles=["super-admin"])
@require_permission(Permission.PLATFORM_MANAGE.value)
def change_tenant_tier(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    tier_slug: str,
):
    """
    Change tenant subscription tier.

    REAL tier change.
    """
    tenant = get_object_or_404(Tenant, id=tenant_id)
    new_tier = get_object_or_404(SubscriptionTier, slug=tier_slug, is_active=True)

    old_tier = tenant.subscription_tier
    old_tier_name = old_tier.name if old_tier else "None"

    tenant.subscription_tier = new_tier
    tenant.save(update_fields=["subscription_tier", "updated_at"])

    # Audit log - REAL
    AuditLog.log(
        action="admin.tier_changed",
        resource_type="Tenant",
        resource_id=str(tenant.id),
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        tenant=tenant,
        details={"old_tier": old_tier_name, "new_tier": new_tier.name},
    )

    return OverrideResult(
        success=True,
        action="change_tier",
        target_id=str(tenant.id),
        target_type="Tenant",
        details={"old_tier": old_tier_name, "new_tier": new_tier.name},
        timestamp=timezone.now().isoformat(),
    )


@router.delete("/tenant/{tenant_id}")
@require_auth(roles=["super-admin"])
@require_permission(Permission.PLATFORM_MANAGE.value)
def delete_tenant(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    confirm: bool = False,
):
    """
    Delete a tenant permanently.

    🔒 Security: Requires confirmation

    REAL deletion with cascade.
    """
    if not confirm:
        raise HttpError(400, "Confirmation required: set confirm=true")

    tenant = get_object_or_404(Tenant, id=tenant_id)
    tenant_name = tenant.name

    # Audit log BEFORE deletion
    AuditLog.log(
        action="admin.tenant_deleted",
        resource_type="Tenant",
        resource_id=str(tenant.id),
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        details={"tenant_name": tenant_name},
    )

    # REAL deletion
    with transaction.atomic():
        # Delete related users first
        TenantUser.objects.filter(tenant_id=tenant_id).delete()
        # Delete API keys
        APIKey.objects.filter(tenant_id=tenant_id).delete()
        # Delete tenant
        tenant.delete()

    return OverrideResult(
        success=True,
        action="delete",
        target_id=str(tenant_id),
        target_type="Tenant",
        details={"tenant_name": tenant_name, "permanently_deleted": True},
        timestamp=timezone.now().isoformat(),
    )


# =============================================================================
# USER OVERRIDE ENDPOINTS
# =============================================================================


@router.post("/user/{user_id}/disable")
@require_auth(roles=["super-admin"])
@require_permission(Permission.PLATFORM_MANAGE.value)
def disable_user(
    request: AuthenticatedRequest,
    user_id: UUID,
    reason: str = "Admin action",
):
    """Disable a user account."""
    user = get_object_or_404(TenantUser, id=user_id)

    user.is_active = False
    user.save(update_fields=["is_active", "updated_at"])

    # Audit log - REAL
    AuditLog.log(
        action="admin.user_disabled",
        resource_type="TenantUser",
        resource_id=str(user.id),
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        tenant=user.tenant,
        details={"email": user.email, "reason": reason},
    )

    return OverrideResult(
        success=True,
        action="disable",
        target_id=str(user.id),
        target_type="TenantUser",
        details={"email": user.email},
        timestamp=timezone.now().isoformat(),
    )


@router.post("/user/{user_id}/enable")
@require_auth(roles=["super-admin"])
@require_permission(Permission.PLATFORM_MANAGE.value)
def enable_user(
    request: AuthenticatedRequest,
    user_id: UUID,
):
    """Enable a disabled user account."""
    user = get_object_or_404(TenantUser, id=user_id)

    user.is_active = True
    user.save(update_fields=["is_active", "updated_at"])

    # Audit log - REAL
    AuditLog.log(
        action="admin.user_enabled",
        resource_type="TenantUser",
        resource_id=str(user.id),
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        tenant=user.tenant,
        details={"email": user.email},
    )

    return OverrideResult(
        success=True,
        action="enable",
        target_id=str(user.id),
        target_type="TenantUser",
        details={"email": user.email},
        timestamp=timezone.now().isoformat(),
    )


# =============================================================================
# SYSTEM OVERRIDE ENDPOINTS
# =============================================================================


@router.post("/revoke-all-api-keys/{tenant_id}")
@require_auth(roles=["super-admin"])
@require_permission(Permission.PLATFORM_MANAGE.value)
def revoke_all_api_keys(
    request: AuthenticatedRequest,
    tenant_id: UUID,
):
    """
    Revoke all API keys for a tenant.

    🔒 Security: Emergency key revocation

    REAL bulk update.
    """
    tenant = get_object_or_404(Tenant, id=tenant_id)

    # REAL bulk update
    count = APIKey.objects.filter(tenant_id=tenant_id, is_active=True).update(
        is_active=False, updated_at=timezone.now()
    )

    # Audit log - REAL
    AuditLog.log(
        action="admin.api_keys_revoked",
        resource_type="Tenant",
        resource_id=str(tenant.id),
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        tenant=tenant,
        details={"revoked_count": count},
    )

    return OverrideResult(
        success=True,
        action="revoke_api_keys",
        target_id=str(tenant_id),
        target_type="Tenant",
        details={"revoked_count": count},
        timestamp=timezone.now().isoformat(),
    )


@router.get("/tenants", response=List[TenantOverride])
@require_auth(roles=["super-admin"])
def list_all_tenants(
    request: AuthenticatedRequest,
    status: Optional[str] = None,
    limit: int = 50,
):
    """
    List all tenants (admin view).

    REAL tenant data.
    """
    queryset = Tenant.objects.all()

    if status:
        queryset = queryset.filter(status=status)

    tenants = queryset.order_by("-created_at")[:limit]

    return [
        TenantOverride(
            tenant_id=str(t.id),
            tenant_name=t.name,
            status=t.status,
            tier=t.subscription_tier.name if t.subscription_tier else "None",
            user_count=TenantUser.objects.filter(tenant_id=t.id).count(),
            created_at=t.created_at.isoformat(),
        )
        for t in tenants
    ]


@router.get("/audit-log")
@require_auth(roles=["super-admin"])
@require_permission(Permission.PLATFORM_MANAGE.value)
def get_admin_audit_log(
    request: AuthenticatedRequest,
    limit: int = 100,
):
    """
    Get admin override audit log.

    🚨 SRE: Override auditing

    REAL audit log data.
    """
    logs = AuditLog.objects.filter(action__startswith="admin.").order_by("-timestamp")[:limit]

    return {
        "logs": [
            {
                "id": str(log.id),
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "actor_id": str(log.actor_id),
                "timestamp": log.timestamp.isoformat(),
                "details": log.details,
            }
            for log in logs
        ]
    }
