"""
User Management Schemas.

Django Ninja schemas for user operations.

ALL 10 PERSONAS - VIBE Coding Rules:
- 🔒 Security: Type-safe schema validation
- 🏛️ Architect: Clean separation of concerns
- 📚 Docs: Comprehensive docstrings
"""

from typing import List, Optional
from uuid import UUID

from ninja import Schema


class UserCreate(Schema):
    """Schema for creating a user."""

    email: str
    display_name: Optional[str] = None
    external_id: Optional[str] = None
    is_active: bool = True
    is_primary: bool = False
    roles: List[str] = []


class UserUpdate(Schema):
    """Schema for updating a user."""

    display_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_primary: Optional[bool] = None


class UserOut(Schema):
    """Schema for user output."""

    id: UUID
    tenant_id: UUID
    email: str
    display_name: Optional[str]
    external_id: Optional[str]
    is_active: bool
    is_primary: bool
    created_at: str
    last_login_at: Optional[str]
    roles: List[dict] = []

    @staticmethod
    def resolve_created_at(obj):
        """Format created_at as ISO string."""
        return obj.created_at.isoformat()

    @staticmethod
    def resolve_last_login_at(obj):
        """Format last_login_at as ISO string if present."""
        return obj.last_login_at.isoformat() if obj.last_login_at else None

    @staticmethod
    def resolve_roles(obj):
        """Get role details for user."""
        from somabrain.aaas.models import TenantUserRole

        assignments = TenantUserRole.objects.filter(tenant_user=obj).select_related("role")
        return [{"id": str(a.role.id), "name": a.role.name, "slug": a.role.slug} for a in assignments]


class UserListOut(Schema):
    """Schema for user list output."""

    id: UUID
    email: str
    display_name: Optional[str]
    is_active: bool
    is_primary: bool
    tenant_name: str
    roles: List[str] = []

    @staticmethod
    def resolve_tenant_name(obj):
        """Get tenant name."""
        return obj.tenant.name if obj.tenant else ""

    @staticmethod
    def resolve_roles(obj):
        """Get role slugs for user."""
        from somabrain.aaas.models import TenantUserRole

        assignments = TenantUserRole.objects.filter(tenant_user=obj).select_related("role")
        return [a.role.slug for a in assignments]


class RoleAssignment(Schema):
    """Schema for assigning a role."""

    role_id: UUID


class UserInvite(Schema):
    """Schema for inviting a user."""

    email: str
    roles: List[str] = []
    message: Optional[str] = None


class UserFilters(Schema):
    """Filters for user list."""

    search: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
