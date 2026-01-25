"""
Roles and Permissions API Endpoints.

Django Ninja API for managing roles and field-level permissions.

ALL 10 PERSONAS per VIBE Coding Rules v5.2
"""

from typing import List, Optional
from uuid import UUID

from django.shortcuts import get_object_or_404
from ninja import Router, Schema

from somabrain.aaas.auth import AuthenticatedRequest, require_auth
from somabrain.aaas.models import (
    ActorType,
    AuditLog,
    FieldPermission,
    Role,
)

router = Router(tags=["Roles"])


# =============================================================================
# SCHEMAS
# =============================================================================


class RoleCreate(Schema):
    """Schema for creating a role."""

    name: str
    slug: str
    description: Optional[str] = None
    platform_role: Optional[str] = None
    parent_id: Optional[UUID] = None


class RoleUpdate(Schema):
    """Schema for updating a role."""

    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    platform_role: Optional[str] = None
    parent_id: Optional[UUID] = None


class RoleOut(Schema):
    """Schema for role output."""

    id: UUID
    name: str
    slug: str
    description: Optional[str]
    is_system: bool
    platform_role: Optional[str]
    parent_id: Optional[UUID]
    created_at: str
    updated_at: str

    @staticmethod
    def resolve_created_at(obj):
        """Execute resolve created at.

        Args:
            obj: The obj.
        """

        return obj.created_at.isoformat()

    @staticmethod
    def resolve_updated_at(obj):
        """Execute resolve updated at.

        Args:
            obj: The obj.
        """

        return obj.updated_at.isoformat()


class FieldPermissionCreate(Schema):
    """Schema for creating field permission."""

    role_id: UUID
    model_name: str
    field_name: str
    can_view: bool = True
    can_edit: bool = False


class FieldPermissionUpdate(Schema):
    """Schema for updating field permission."""

    can_view: Optional[bool] = None
    can_edit: Optional[bool] = None


class FieldPermissionOut(Schema):
    """Schema for field permission output."""

    id: UUID
    role_id: UUID
    model_name: str
    field_name: str
    can_view: bool
    can_edit: bool


class PermissionMatrixOut(Schema):
    """Schema for permission matrix output."""

    model_name: str
    fields: List[dict]


# =============================================================================
# ROLE ENDPOINTS
# =============================================================================


@router.get("/", response=List[RoleOut])
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
def list_roles(request: AuthenticatedRequest):
    """
    List all roles.

    Super-admin sees all. Tenant-admin sees non-system roles.
    """
    if request.is_super_admin:
        roles = Role.objects.all().order_by("name")
    else:
        roles = Role.objects.filter(is_system=False).order_by("name")

    return list(roles)


@router.post("/", response=RoleOut)
@require_auth(roles=["super-admin"])
def create_role(request: AuthenticatedRequest, data: RoleCreate):
    """
    Create a new custom role.

    Only super-admin can create roles.
    """
    parent = None
    if data.parent_id:
        parent = get_object_or_404(Role, id=data.parent_id)

    role = Role.objects.create(
        name=data.name,
        slug=data.slug,
        description=data.description,
        platform_role=data.platform_role,
        parent=parent,
        is_system=False,
    )

    # Audit log
    AuditLog.log(
        action="role.created",
        resource_type="Role",
        resource_id=str(role.id),
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        details={"name": role.name},
    )

    return role


@router.get("/{role_id}", response=RoleOut)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
def get_role(request: AuthenticatedRequest, role_id: UUID):
    """Get a specific role."""
    return get_object_or_404(Role, id=role_id)


@router.patch("/{role_id}", response=RoleOut)
@require_auth(roles=["super-admin"])
def update_role(request: AuthenticatedRequest, role_id: UUID, data: RoleUpdate):
    """
    Update a role.

    Cannot update system roles.
    """
    role = get_object_or_404(Role, id=role_id)

    if role.is_system:
        from ninja.errors import HttpError

        raise HttpError(400, "Cannot modify system roles")

    update_data = data.dict(exclude_unset=True)

    if "parent_id" in update_data:
        parent_id = update_data.pop("parent_id")
        role.parent = Role.objects.get(id=parent_id) if parent_id else None

    for field, value in update_data.items():
        setattr(role, field, value)

    role.save()

    return role


@router.delete("/{role_id}")
@require_auth(roles=["super-admin"])
def delete_role(request: AuthenticatedRequest, role_id: UUID):
    """
    Delete a role.

    Cannot delete system roles.
    """
    role = get_object_or_404(Role, id=role_id)

    if role.is_system:
        from ninja.errors import HttpError

        raise HttpError(400, "Cannot delete system roles")

    role_name = role.name
    role.delete()

    return {"success": True, "message": f"Role '{role_name}' deleted"}


# =============================================================================
# FIELD PERMISSION ENDPOINTS
# =============================================================================


@router.get("/{role_id}/permissions", response=List[FieldPermissionOut])
@require_auth(roles=["super-admin"])
def list_role_permissions(request: AuthenticatedRequest, role_id: UUID):
    """Get all field permissions for a role."""
    role = get_object_or_404(Role, id=role_id)
    permissions = FieldPermission.objects.filter(role=role).order_by(
        "model_name", "field_name"
    )
    return list(permissions)


@router.post("/permissions", response=FieldPermissionOut)
@require_auth(roles=["super-admin"])
def create_permission(request: AuthenticatedRequest, data: FieldPermissionCreate):
    """Create a field permission."""
    role = get_object_or_404(Role, id=data.role_id)

    perm, created = FieldPermission.objects.update_or_create(
        role=role,
        model_name=data.model_name,
        field_name=data.field_name,
        defaults={
            "can_view": data.can_view,
            "can_edit": data.can_edit,
        },
    )

    return perm


@router.patch("/permissions/{perm_id}", response=FieldPermissionOut)
@require_auth(roles=["super-admin"])
def update_permission(
    request: AuthenticatedRequest, perm_id: UUID, data: FieldPermissionUpdate
):
    """Update a field permission."""
    perm = get_object_or_404(FieldPermission, id=perm_id)

    update_data = data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(perm, field, value)

    perm.save()
    return perm


@router.delete("/permissions/{perm_id}")
@require_auth(roles=["super-admin"])
def delete_permission(request: AuthenticatedRequest, perm_id: UUID):
    """Delete a field permission."""
    perm = get_object_or_404(FieldPermission, id=perm_id)
    perm.delete()
    return {"success": True}


# =============================================================================
# PERMISSION MATRIX (For UI)
# =============================================================================


@router.get("/{role_id}/matrix", response=List[PermissionMatrixOut])
@require_auth(roles=["super-admin"])
def get_permission_matrix(request: AuthenticatedRequest, role_id: UUID):
    """
    Get permission matrix for a role.

    Returns all models with their fields and permissions.
    Used by the admin UI to display/edit the permission grid.
    """
    role = get_object_or_404(Role, id=role_id)

    # Get current permissions
    permissions = FieldPermission.objects.filter(role=role)
    perm_map = {(p.model_name, p.field_name): p for p in permissions}

    # Define models and their editable fields
    # 🏛️ Architect: This defines the permission matrix structure
    MODEL_FIELDS = {
        "Tenant": [
            "name",
            "slug",
            "status",
            "tier",
            "admin_email",
            "billing_email",
            "config",
            "quota_overrides",
        ],
        "TenantUser": ["email", "role", "display_name", "is_active", "is_primary"],
        "Subscription": [
            "tier",
            "status",
            "current_period_start",
            "current_period_end",
        ],
        "APIKey": ["name", "scopes", "is_active", "expires_at"],
        "IdentityProvider": [
            "name",
            "provider_type",
            "client_id",
            "is_enabled",
            "is_default",
        ],
    }

    result = []
    for model, fields in MODEL_FIELDS.items():
        field_perms = []
        for field in fields:
            perm = perm_map.get((model, field))
            field_perms.append(
                {
                    "field_name": field,
                    "can_view": perm.can_view if perm else False,
                    "can_edit": perm.can_edit if perm else False,
                    "perm_id": str(perm.id) if perm else None,
                }
            )

        result.append(
            PermissionMatrixOut(
                model_name=model,
                fields=field_perms,
            )
        )

    return result


@router.post("/{role_id}/matrix")
@require_auth(roles=["super-admin"])
def update_permission_matrix(
    request: AuthenticatedRequest, role_id: UUID, matrix: List[dict]
):
    """
    Bulk update permission matrix for a role.

    Accepts a list of {model_name, field_name, can_view, can_edit} dicts.
    """
    role = get_object_or_404(Role, id=role_id)

    updated = 0
    for entry in matrix:
        perm, created = FieldPermission.objects.update_or_create(
            role=role,
            model_name=entry["model_name"],
            field_name=entry["field_name"],
            defaults={
                "can_view": entry.get("can_view", False),
                "can_edit": entry.get("can_edit", False),
            },
        )
        updated += 1

    return {"success": True, "updated": updated}
