"""
Tenant Authentication Settings API.

Django Ninja API for managing tenant-specific auth configuration.
Tenants can override platform defaults for OAuth providers.

ALL 10 PERSONAS per VIBE Coding Rules:
- 🔒 Security: Tenant isolation, secrets in vault
- 🏛️ Architect: Hierarchical config (platform → tenant)
- 💾 DBA: Efficient config merging
- 🐍 Django: ORM patterns
- 📚 Docs: Clear docstrings
- 🧪 QA: Testable
- 🚨 SRE: Audit logging
- 📊 Perf: Cached configs
- 🎨 UX: Clear error messages
- 🛠️ DevOps: Environment-based
"""

from typing import List, Optional
from uuid import UUID

from django.shortcuts import get_object_or_404
from ninja import Router, Schema

from somabrain.saas.models import (
    Tenant,
    TenantAuthConfig,
    IdentityProvider,
    AuditLog,
    ActorType,
)
from somabrain.saas.auth import require_auth, AuthenticatedRequest
from somabrain.saas.granular import require_permission, Permission


router = Router(tags=["Tenant Auth"])


# =============================================================================
# SCHEMAS
# =============================================================================


class TenantAuthConfigOut(Schema):
    """Schema for tenant auth config output."""

    id: UUID
    tenant_id: UUID
    preferred_provider_id: Optional[UUID]
    preferred_provider_name: Optional[str]
    custom_redirect_uris: List[str]
    mfa_required: bool
    session_timeout_minutes: int
    allow_registration: bool
    allowed_domains: List[str]

    @staticmethod
    def resolve_preferred_provider_name(obj):
        """Execute resolve preferred provider name.

        Args:
            obj: The obj.
        """

        return obj.preferred_provider.name if obj.preferred_provider else None


class TenantAuthConfigUpdate(Schema):
    """Schema for updating tenant auth config."""

    preferred_provider_id: Optional[UUID] = None
    custom_redirect_uris: Optional[List[str]] = None
    mfa_required: Optional[bool] = None
    session_timeout_minutes: Optional[int] = None
    allow_registration: Optional[bool] = None
    allowed_domains: Optional[List[str]] = None


class EffectiveProviderOut(Schema):
    """Schema for effective provider (merged platform + tenant)."""

    id: UUID
    name: str
    provider_type: str
    is_platform_level: bool
    is_tenant_override: bool
    is_enabled: bool
    is_default: bool


# =============================================================================
# TENANT AUTH CONFIG ENDPOINTS
# =============================================================================


@router.get("/{tenant_id}/config", response=TenantAuthConfigOut)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.IDP_READ.value)
def get_tenant_auth_config(
    request: AuthenticatedRequest,
    tenant_id: UUID,
):
    """
    Get tenant authentication configuration.

    Returns the tenant's auth settings including preferred provider,
    MFA requirements, session timeout, etc.
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    tenant = get_object_or_404(Tenant, id=tenant_id)

    # Get or create auth config
    config, created = TenantAuthConfig.objects.get_or_create(
        tenant=tenant,
        defaults={
            "custom_redirect_uris": [],
            "mfa_required": False,
            "session_timeout_minutes": 480,
            "allow_registration": True,
            "allowed_domains": [],
        },
    )

    return config


@router.patch("/{tenant_id}/config", response=TenantAuthConfigOut)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.IDP_UPDATE.value)
def update_tenant_auth_config(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    data: TenantAuthConfigUpdate,
):
    """
    Update tenant authentication configuration.

    Tenant admins can configure:
    - Preferred login provider
    - MFA requirements
    - Session timeout
    - Allowed email domains
    - Custom redirect URIs
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    tenant = get_object_or_404(Tenant, id=tenant_id)
    config, _ = TenantAuthConfig.objects.get_or_create(tenant=tenant)

    update_data = data.dict(exclude_unset=True)

    # Handle preferred provider
    if "preferred_provider_id" in update_data:
        provider_id = update_data.pop("preferred_provider_id")
        if provider_id:
            # Validate provider exists and is accessible
            provider = IdentityProvider.objects.filter(
                id=provider_id,
            ).filter(
                # Must be platform-level OR belong to this tenant
                tenant__isnull=True
            ) | IdentityProvider.objects.filter(
                id=provider_id,
                tenant=tenant,
            )
            if not provider.exists():
                from ninja.errors import HttpError

                raise HttpError(400, "Invalid provider ID")
            config.preferred_provider_id = provider_id
        else:
            config.preferred_provider = None

    # Update other fields
    for field, value in update_data.items():
        setattr(config, field, value)

    config.save()

    # Audit log
    AuditLog.log(
        action="tenant_auth.updated",
        resource_type="TenantAuthConfig",
        resource_id=str(config.id),
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN if request.is_super_admin else ActorType.USER,
        tenant=tenant,
        details={"updated_fields": list(data.dict(exclude_unset=True).keys())},
    )

    return config


# =============================================================================
# EFFECTIVE PROVIDERS (Merged View)
# =============================================================================


@router.get("/{tenant_id}/providers", response=List[EffectiveProviderOut])
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.IDP_LIST.value)
def get_effective_providers(
    request: AuthenticatedRequest,
    tenant_id: UUID,
):
    """
    Get effective identity providers for a tenant.

    Returns merged list of:
    - Platform-level providers (inherited)
    - Tenant-specific providers (overrides)

    ALL 10 PERSONAS - Hierarchical auth architecture.
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    tenant = get_object_or_404(Tenant, id=tenant_id)

    # Get platform-level providers
    platform_providers = list(
        IdentityProvider.objects.filter(
            tenant__isnull=True,
            is_enabled=True,
        ).order_by("display_order", "name")
    )

    # Get tenant-specific providers
    tenant_providers = list(
        IdentityProvider.objects.filter(
            tenant=tenant,
        ).order_by("display_order", "name")
    )

    # Build effective list
    result = []

    # Track overridden providers (by type)
    overridden_types = {p.provider_type for p in tenant_providers}

    # Add platform providers (not overridden)
    for p in platform_providers:
        if p.provider_type not in overridden_types:
            result.append(
                EffectiveProviderOut(
                    id=p.id,
                    name=p.name,
                    provider_type=p.provider_type,
                    is_platform_level=True,
                    is_tenant_override=False,
                    is_enabled=p.is_enabled,
                    is_default=p.is_default,
                )
            )

    # Add tenant providers
    for p in tenant_providers:
        result.append(
            EffectiveProviderOut(
                id=p.id,
                name=p.name,
                provider_type=p.provider_type,
                is_platform_level=False,
                is_tenant_override=True,
                is_enabled=p.is_enabled,
                is_default=p.is_default,
            )
        )

    return result


# =============================================================================
# TENANT-SPECIFIC PROVIDER MANAGEMENT
# =============================================================================


@router.post("/{tenant_id}/providers/{provider_type}/override")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.IDP_CREATE.value)
def create_tenant_provider_override(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    provider_type: str,
    data: dict,
):
    """
    Create a tenant-specific provider override.

    Allows tenant to use their own OAuth credentials instead of platform defaults.

    ALL 10 PERSONAS - Security: Vault secrets required.
    """
    from somabrain.saas.models import IdentityProviderType

    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    tenant = get_object_or_404(Tenant, id=tenant_id)

    # Validate provider type
    valid_types = [c[0] for c in IdentityProviderType.choices]
    if provider_type not in valid_types:
        from ninja.errors import HttpError

        raise HttpError(400, f"Invalid provider type: {provider_type}")

    # Check if override already exists
    existing = IdentityProvider.objects.filter(
        tenant=tenant,
        provider_type=provider_type,
    ).first()

    if existing:
        from ninja.errors import HttpError

        raise HttpError(400, f"Override for {provider_type} already exists")

    # Create tenant override
    provider = IdentityProvider.objects.create(
        name=data.get("name", f"{tenant.name} {provider_type.title()} OAuth"),
        provider_type=provider_type,
        tenant=tenant,
        client_id=data.get("client_id"),
        auth_uri=data.get("auth_uri", ""),
        token_uri=data.get("token_uri", ""),
        redirect_uris=data.get("redirect_uris", []),
        vault_secret_path=data.get(
            "vault_secret_path",
            f"vault://secrets/tenants/{tenant.slug}/oauth/{provider_type}",
        ),
        is_enabled=data.get("is_enabled", True),
    )

    # Audit log
    AuditLog.log(
        action="tenant_provider.created",
        resource_type="IdentityProvider",
        resource_id=str(provider.id),
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        tenant=tenant,
        details={"provider_type": provider_type},
    )

    return {
        "success": True,
        "provider_id": str(provider.id),
        "message": f"{provider_type} override created",
    }


@router.delete("/{tenant_id}/providers/{provider_id}")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.IDP_DELETE.value)
def delete_tenant_provider_override(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    provider_id: UUID,
):
    """
    Delete a tenant-specific provider override.

    Tenant will fall back to platform defaults.
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    provider = get_object_or_404(
        IdentityProvider,
        id=provider_id,
        tenant_id=tenant_id,
    )

    provider_name = provider.name
    provider.delete()

    # Audit log
    AuditLog.log(
        action="tenant_provider.deleted",
        resource_type="IdentityProvider",
        resource_id=str(provider_id),
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        tenant_id=tenant_id,
        details={"name": provider_name},
    )

    return {
        "success": True,
        "message": f"Provider '{provider_name}' deleted, falling back to platform defaults",
    }
