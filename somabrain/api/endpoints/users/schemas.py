"""
User Management Schemas.

Django Ninja schemas for user operations.

ALL 10 PERSONAS - VIBE Coding Rules:
- 🔒 Security: Type-safe schema validation
- 🏛️ Architect: Clean separation of concerns
- 📚 Docs: Comprehensive docstrings
"""

from uuid import UUID

from ninja import Schema


class UserCreate(Schema):
    """Schema for creating a user."""

    email: str
    display_name: str | None = None
    external_id: str | None = None
    is_active: bool = True
    is_primary: bool = False
    roles: list[str] = []


class UserUpdate(Schema):
    """Schema for updating a user."""

    display_name: str | None = None
    is_active: bool | None = None
    is_primary: bool | None = None


class UserOut(Schema):
    """Schema for user output."""

    id: UUID
    tenant_id: UUID
    email: str
    display_name: str | None
    external_id: str | None
    is_active: bool
    is_primary: bool
    created_at: str
    last_login_at: str | None
    roles: list[dict] = []

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

        assignments = TenantUserRole.objects.filter(tenant_user=obj).select_related(
            "role"
        )
        return [
            {"id": str(a.role.id), "name": a.role.name, "slug": a.role.slug}
            for a in assignments
        ]


class UserListOut(Schema):
    """Schema for user list output."""

    id: UUID
    email: str
    display_name: str | None
    is_active: bool
    is_primary: bool
    tenant_name: str
    roles: list[str] = []

    @staticmethod
    def resolve_tenant_name(obj):
        """Get tenant name."""
        return obj.tenant.name if obj.tenant else ""

    @staticmethod
    def resolve_roles(obj):
        """Get role slugs for user."""
        from somabrain.aaas.models import TenantUserRole

        assignments = TenantUserRole.objects.filter(tenant_user=obj).select_related(
            "role"
        )
        return [a.role.slug for a in assignments]


class RoleAssignment(Schema):
    """Schema for assigning a role."""

    role_id: UUID


class UserInvite(Schema):
    """Schema for inviting a user."""

    email: str
    roles: list[str] = []
    message: str | None = None


class UserFilters(Schema):
    """Filters for user list."""

    search: str | None = None
    role: str | None = None
    status: str | None = None
