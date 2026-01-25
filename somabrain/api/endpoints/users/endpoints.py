"""
User Management API Endpoints.

Django Ninja API for managing tenant users, role assignments, and invitations.

ALL 10 PERSONAS per VIBE Coding Rules:
- 🔒 Security: Tenant isolation, role verification
- 🏛️ Architect: Clean layered design
- 💾 DBA: Efficient queries with select_related
- 🐍 Django: ORM best practices
- 📚 Docs: Comprehensive docstrings
- 🧪 QA: Testable interfaces
- 🚨 SRE: Audit logging
- 📊 Perf: Pagination support
- 🎨 UX: Clear error messages
- 🛠️ DevOps: Environment-based config
"""

from typing import List
from uuid import UUID

from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja import Query, Router
from ninja.errors import HttpError

from somabrain.aaas.auth import AuthenticatedRequest, require_auth
from somabrain.aaas.granular import Permission, require_permission
from somabrain.aaas.models import ActorType, AuditLog, Role, Tenant, TenantUser, TenantUserRole

from .schemas import RoleAssignment, UserCreate, UserFilters, UserInvite, UserListOut, UserOut, UserUpdate

router = Router(tags=["Users"])


# =============================================================================
# PLATFORM USER ENDPOINTS (SysAdmin)
# =============================================================================


@router.get("/", response=List[UserListOut])
@require_auth(roles=["super-admin"])
@require_permission(Permission.USERS_LIST.value)
def list_all_users(request: AuthenticatedRequest, filters: UserFilters = Query(...)):
    """List all users across all tenants. SysAdmin only."""
    queryset = TenantUser.objects.select_related("tenant").all()

    if filters.search:
        queryset = queryset.filter(Q(email__icontains=filters.search) | Q(display_name__icontains=filters.search))
    if filters.status == "active":
        queryset = queryset.filter(is_active=True)
    elif filters.status == "inactive":
        queryset = queryset.filter(is_active=False)
    if filters.role:
        user_ids = TenantUserRole.objects.filter(role__slug=filters.role).values_list("tenant_user_id", flat=True)
        queryset = queryset.filter(id__in=user_ids)

    return list(queryset.order_by("-created_at")[:100])


# =============================================================================
# TENANT USER ENDPOINTS
# =============================================================================


@router.get("/tenant/{tenant_id}", response=List[UserListOut])
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.USERS_LIST.value)
def list_tenant_users(request: AuthenticatedRequest, tenant_id: UUID, filters: UserFilters = Query(...)):
    """List users for a specific tenant."""
    if not request.is_super_admin and str(request.tenant_id) != str(tenant_id):
        raise HttpError(403, "Access denied to this tenant")

    tenant = get_object_or_404(Tenant, id=tenant_id)
    queryset = TenantUser.objects.filter(tenant=tenant).select_related("tenant")

    if filters.search:
        queryset = queryset.filter(Q(email__icontains=filters.search) | Q(display_name__icontains=filters.search))
    if filters.status == "active":
        queryset = queryset.filter(is_active=True)
    elif filters.status == "inactive":
        queryset = queryset.filter(is_active=False)

    return list(queryset.order_by("-created_at"))


@router.post("/tenant/{tenant_id}", response=UserOut)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.USERS_CREATE.value)
def create_tenant_user(request: AuthenticatedRequest, tenant_id: UUID, data: UserCreate):
    """Create a new user in a tenant with audit logging."""
    if not request.is_super_admin and str(request.tenant_id) != str(tenant_id):
        raise HttpError(403, "Access denied to this tenant")

    tenant = get_object_or_404(Tenant, id=tenant_id)
    if TenantUser.objects.filter(tenant=tenant, email=data.email).exists():
        raise HttpError(400, f"User with email {data.email} already exists in this tenant")

    with transaction.atomic():
        user = TenantUser.objects.create(
            tenant=tenant, email=data.email, display_name=data.display_name,
            external_id=data.external_id, is_active=data.is_active, is_primary=data.is_primary)
        if data.roles:
            roles = Role.objects.filter(slug__in=data.roles)
            for role in roles:
                TenantUserRole.objects.create(tenant_user=user, role=role, assigned_by_id=request.user_id)
        AuditLog.log(action="user.created", resource_type="TenantUser", resource_id=str(user.id),
            actor_id=str(request.user_id), actor_type=ActorType.ADMIN if request.is_super_admin else ActorType.USER,
            tenant=tenant, details={"email": user.email, "roles": data.roles})
    return user


@router.get("/tenant/{tenant_id}/{user_id}", response=UserOut)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.USERS_READ.value)
def get_tenant_user(request: AuthenticatedRequest, tenant_id: UUID, user_id: UUID):
    """Get a specific user in a tenant."""
    if not request.is_super_admin and str(request.tenant_id) != str(tenant_id):
        raise HttpError(403, "Access denied")
    return get_object_or_404(TenantUser, id=user_id, tenant_id=tenant_id)


@router.patch("/tenant/{tenant_id}/{user_id}", response=UserOut)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.USERS_UPDATE.value)
def update_tenant_user(request: AuthenticatedRequest, tenant_id: UUID, user_id: UUID, data: UserUpdate):
    """Update a user in a tenant with audit logging."""
    if not request.is_super_admin and str(request.tenant_id) != str(tenant_id):
        raise HttpError(403, "Access denied")
    user = get_object_or_404(TenantUser, id=user_id, tenant_id=tenant_id)
    update_data = data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    user.save()
    AuditLog.log(action="user.updated", resource_type="TenantUser", resource_id=str(user.id),
        actor_id=str(request.user_id), actor_type=ActorType.ADMIN if request.is_super_admin else ActorType.USER,
        tenant=user.tenant, details={"updated_fields": list(update_data.keys())})
    return user


@router.delete("/tenant/{tenant_id}/{user_id}")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.USERS_DELETE.value)
def delete_tenant_user(request: AuthenticatedRequest, tenant_id: UUID, user_id: UUID):
    """Delete a user from a tenant."""
    if not request.is_super_admin and str(request.tenant_id) != str(tenant_id):
        raise HttpError(403, "Access denied")
    user = get_object_or_404(TenantUser, id=user_id, tenant_id=tenant_id)
    if user.is_primary:
        raise HttpError(400, "Cannot delete primary tenant user")
    email = user.email
    user.delete()
    AuditLog.log(action="user.deleted", resource_type="TenantUser", resource_id=str(user_id),
        actor_id=str(request.user_id), actor_type=ActorType.ADMIN if request.is_super_admin else ActorType.USER,
        tenant_id=tenant_id, details={"email": email})
    return {"success": True, "message": f"User '{email}' deleted"}


# =============================================================================
# ROLE ASSIGNMENT ENDPOINTS
# =============================================================================


@router.post("/tenant/{tenant_id}/{user_id}/roles")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.USERS_ASSIGN_ROLE.value)
def assign_role(request: AuthenticatedRequest, tenant_id: UUID, user_id: UUID, data: RoleAssignment):
    """Assign a role to a user."""
    if not request.is_super_admin and str(request.tenant_id) != str(tenant_id):
        raise HttpError(403, "Access denied")
    user = get_object_or_404(TenantUser, id=user_id, tenant_id=tenant_id)
    role = get_object_or_404(Role, id=data.role_id)
    if TenantUserRole.objects.filter(tenant_user=user, role=role).exists():
        raise HttpError(400, f"Role '{role.name}' already assigned")
    TenantUserRole.objects.create(tenant_user=user, role=role, assigned_by_id=request.user_id)
    AuditLog.log(action="user.role_assigned", resource_type="TenantUserRole", resource_id=str(user.id),
        actor_id=str(request.user_id), actor_type=ActorType.ADMIN, tenant=user.tenant, details={"role": role.name})
    return {"success": True, "message": f"Role '{role.name}' assigned"}


@router.delete("/tenant/{tenant_id}/{user_id}/roles/{role_id}")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.USERS_ASSIGN_ROLE.value)
def remove_role(request: AuthenticatedRequest, tenant_id: UUID, user_id: UUID, role_id: UUID):
    """Remove a role from a user."""
    if not request.is_super_admin and str(request.tenant_id) != str(tenant_id):
        raise HttpError(403, "Access denied")
    user = get_object_or_404(TenantUser, id=user_id, tenant_id=tenant_id)
    role = get_object_or_404(Role, id=role_id)
    assignment = TenantUserRole.objects.filter(tenant_user=user, role=role).first()
    if not assignment:
        raise HttpError(404, f"Role '{role.name}' not assigned to user")
    assignment.delete()
    AuditLog.log(action="user.role_removed", resource_type="TenantUserRole", resource_id=str(user.id),
        actor_id=str(request.user_id), actor_type=ActorType.ADMIN, tenant=user.tenant, details={"role": role.name})
    return {"success": True, "message": f"Role '{role.name}' removed"}


# =============================================================================
# USER INVITATION & STATUS
# =============================================================================


@router.post("/tenant/{tenant_id}/invite")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.USERS_INVITE.value)
def invite_user(request: AuthenticatedRequest, tenant_id: UUID, data: UserInvite):
    """Invite a user to a tenant with email notification."""
    if not request.is_super_admin and str(request.tenant_id) != str(tenant_id):
        raise HttpError(403, "Access denied")
    tenant = get_object_or_404(Tenant, id=tenant_id)
    if TenantUser.objects.filter(tenant=tenant, email=data.email).exists():
        raise HttpError(400, f"User with email {data.email} already exists")
    user = TenantUser.objects.create(tenant=tenant, email=data.email, is_active=False)
    if data.roles:
        roles = Role.objects.filter(slug__in=data.roles)
        for role in roles:
            TenantUserRole.objects.create(tenant_user=user, role=role, assigned_by_id=request.user_id)
    from somabrain.aaas.email_service import send_invitation_email
    email_sent = send_invitation_email(to_email=data.email, tenant_name=tenant.name,
        inviter_name=getattr(request, "user_display_name", None), custom_message=getattr(data, "message", None))
    AuditLog.log(action="user.invited", resource_type="TenantUser", resource_id=str(user.id),
        actor_id=str(request.user_id), actor_type=ActorType.ADMIN, tenant=tenant,
        details={"email": data.email, "roles": data.roles, "email_sent": email_sent})
    return {"success": True, "message": f"Invitation sent to {data.email}", "user_id": str(user.id)}


@router.post("/tenant/{tenant_id}/{user_id}/toggle-status")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.USERS_UPDATE.value)
def toggle_user_status(request: AuthenticatedRequest, tenant_id: UUID, user_id: UUID):
    """Enable/disable a user."""
    if not request.is_super_admin and str(request.tenant_id) != str(tenant_id):
        raise HttpError(403, "Access denied")
    user = get_object_or_404(TenantUser, id=user_id, tenant_id=tenant_id)
    if user.is_primary and user.is_active:
        raise HttpError(400, "Cannot disable primary tenant user")
    user.is_active = not user.is_active
    user.save()
    action = "enabled" if user.is_active else "disabled"
    AuditLog.log(action=f"user.{action}", resource_type="TenantUser", resource_id=str(user.id),
        actor_id=str(request.user_id), actor_type=ActorType.ADMIN, tenant=user.tenant, details={"is_active": user.is_active})
    return {"success": True, "is_active": user.is_active, "message": f"User {action}"}


@router.get("/tenant/{tenant_id}/{user_id}/audit", response=List[dict])
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.AUDIT_READ.value)
def get_user_audit_log(request: AuthenticatedRequest, tenant_id: UUID, user_id: UUID):
    """Get audit log for a specific user."""
    if not request.is_super_admin and str(request.tenant_id) != str(tenant_id):
        raise HttpError(403, "Access denied")
    user = get_object_or_404(TenantUser, id=user_id, tenant_id=tenant_id)
    logs = AuditLog.objects.filter(resource_type="TenantUser", resource_id=str(user.id)).order_by("-timestamp")[:50]
    return [{"action": log.action, "timestamp": log.timestamp.isoformat(), "actor_id": log.actor_id, "details": log.details} for log in logs]
