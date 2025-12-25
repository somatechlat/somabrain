"""
Identity Provider API Endpoints.

Django Ninja API for managing OAuth identity providers.
Supports: Google, Facebook, GitHub, Keycloak, Generic OIDC.

All secrets referenced via vault path - NEVER stored in database.
"""

from typing import List, Optional
from uuid import UUID

from django.shortcuts import get_object_or_404
from ninja import Router, Schema, Field
from ninja.security import HttpBearer

from somabrain.saas.models import (
    IdentityProvider,
    IdentityProviderType,
    TenantAuthConfig,
    AuditLog,
    ActorType,
)
from somabrain.saas.auth import require_auth, AuthenticatedRequest


router = Router(tags=["Identity Providers"])


# =============================================================================
# SCHEMAS
# =============================================================================

class IdentityProviderBase(Schema):
    """Base schema for identity provider."""
    name: str
    provider_type: str
    client_id: str
    project_id: Optional[str] = None
    auth_uri: str
    token_uri: str
    certs_url: Optional[str] = None
    redirect_uris: List[str] = []
    javascript_origins: List[str] = []
    default_scopes: List[str] = ["openid", "email", "profile"]
    claim_mappings: dict = {}
    vault_secret_path: str
    is_enabled: bool = True
    is_default: bool = False
    trust_email: bool = True
    store_token: bool = True
    display_order: int = 0


class IdentityProviderCreate(IdentityProviderBase):
    """Schema for creating identity provider."""
    tenant_id: Optional[UUID] = None  # None = platform level


class IdentityProviderUpdate(Schema):
    """Schema for updating identity provider."""
    name: Optional[str] = None
    client_id: Optional[str] = None
    project_id: Optional[str] = None
    auth_uri: Optional[str] = None
    token_uri: Optional[str] = None
    certs_url: Optional[str] = None
    redirect_uris: Optional[List[str]] = None
    javascript_origins: Optional[List[str]] = None
    default_scopes: Optional[List[str]] = None
    claim_mappings: Optional[dict] = None
    vault_secret_path: Optional[str] = None
    is_enabled: Optional[bool] = None
    is_default: Optional[bool] = None
    trust_email: Optional[bool] = None
    store_token: Optional[bool] = None
    display_order: Optional[int] = None


class IdentityProviderOut(IdentityProviderBase):
    """Schema for identity provider output."""
    id: UUID
    tenant_id: Optional[UUID] = None
    created_at: str
    updated_at: str

    @staticmethod
    def resolve_created_at(obj):
        return obj.created_at.isoformat()

    @staticmethod
    def resolve_updated_at(obj):
        return obj.updated_at.isoformat()


class IdentityProviderListOut(Schema):
    """Schema for listing identity providers."""
    id: UUID
    name: str
    provider_type: str
    tenant_id: Optional[UUID] = None
    is_enabled: bool
    is_default: bool
    display_order: int


class TestConnectionRequest(Schema):
    """Schema for testing provider connection."""
    provider_id: Optional[UUID] = None
    provider_data: Optional[IdentityProviderBase] = None


class TestConnectionResult(Schema):
    """Schema for connection test result."""
    success: bool
    message: str
    details: Optional[dict] = None


# =============================================================================
# PLATFORM LEVEL ENDPOINTS (SysAdmin)
# =============================================================================

@router.get("/platform", response=List[IdentityProviderListOut])
@require_auth(roles=["super-admin"])
def list_platform_providers(request: AuthenticatedRequest):
    """
    List all platform-level identity providers.
    
    SysAdmin only - these are defaults for all tenants.
    """
    providers = IdentityProvider.objects.filter(tenant__isnull=True).order_by("display_order", "name")
    return list(providers)


@router.post("/platform", response=IdentityProviderOut)
@require_auth(roles=["super-admin"])
def create_platform_provider(request: AuthenticatedRequest, data: IdentityProviderCreate):
    """
    Create a new platform-level identity provider.
    
    SysAdmin only. Provider will be available to all tenants as default.
    """
    # Validate provider type
    if data.provider_type not in [c[0] for c in IdentityProviderType.choices]:
        return {"error": f"Invalid provider type: {data.provider_type}"}, 400
    
    # If setting as default, unset other defaults
    if data.is_default:
        IdentityProvider.objects.filter(
            tenant__isnull=True, 
            is_default=True
        ).update(is_default=False)
    
    provider = IdentityProvider.objects.create(
        name=data.name,
        provider_type=data.provider_type,
        tenant=None,  # Platform level
        client_id=data.client_id,
        project_id=data.project_id,
        auth_uri=data.auth_uri,
        token_uri=data.token_uri,
        certs_url=data.certs_url,
        redirect_uris=data.redirect_uris,
        javascript_origins=data.javascript_origins,
        default_scopes=data.default_scopes,
        claim_mappings=data.claim_mappings,
        vault_secret_path=data.vault_secret_path,
        is_enabled=data.is_enabled,
        is_default=data.is_default,
        trust_email=data.trust_email,
        store_token=data.store_token,
        display_order=data.display_order,
    )
    
    # Audit log
    AuditLog.log(
        action="identity_provider.created",
        resource_type="IdentityProvider",
        resource_id=str(provider.id),
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        details={"name": provider.name, "type": provider.provider_type, "scope": "platform"},
    )
    
    return provider


@router.get("/platform/{provider_id}", response=IdentityProviderOut)
@require_auth(roles=["super-admin"])
def get_platform_provider(request: AuthenticatedRequest, provider_id: UUID):
    """Get a specific platform-level identity provider."""
    provider = get_object_or_404(IdentityProvider, id=provider_id, tenant__isnull=True)
    return provider


@router.patch("/platform/{provider_id}", response=IdentityProviderOut)
@require_auth(roles=["super-admin"])
def update_platform_provider(request: AuthenticatedRequest, provider_id: UUID, data: IdentityProviderUpdate):
    """Update a platform-level identity provider."""
    provider = get_object_or_404(IdentityProvider, id=provider_id, tenant__isnull=True)
    
    # Update fields that are provided
    update_data = data.dict(exclude_unset=True)
    
    # If setting as default, unset other defaults
    if update_data.get("is_default"):
        IdentityProvider.objects.filter(
            tenant__isnull=True,
            is_default=True
        ).exclude(id=provider_id).update(is_default=False)
    
    for field, value in update_data.items():
        setattr(provider, field, value)
    
    provider.save()
    
    # Audit log
    AuditLog.log(
        action="identity_provider.updated",
        resource_type="IdentityProvider",
        resource_id=str(provider.id),
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        details={"updated_fields": list(update_data.keys())},
    )
    
    return provider


@router.delete("/platform/{provider_id}")
@require_auth(roles=["super-admin"])
def delete_platform_provider(request: AuthenticatedRequest, provider_id: UUID):
    """Delete a platform-level identity provider."""
    provider = get_object_or_404(IdentityProvider, id=provider_id, tenant__isnull=True)
    
    provider_name = provider.name
    provider.delete()
    
    # Audit log
    AuditLog.log(
        action="identity_provider.deleted",
        resource_type="IdentityProvider",
        resource_id=str(provider_id),
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        details={"name": provider_name},
    )
    
    return {"success": True, "message": f"Provider '{provider_name}' deleted"}


# =============================================================================
# TENANT LEVEL ENDPOINTS
# =============================================================================

@router.get("/tenant/{tenant_id}", response=List[IdentityProviderListOut])
@require_auth(roles=["super-admin", "tenant-admin"])
def list_tenant_providers(request: AuthenticatedRequest, tenant_id: UUID):
    """
    List identity providers for a specific tenant.
    
    Includes both tenant-specific and inherited platform providers.
    """
    # Tenant-specific providers
    tenant_providers = list(
        IdentityProvider.objects.filter(tenant_id=tenant_id).order_by("display_order", "name")
    )
    
    # Platform providers (inherited)
    platform_providers = list(
        IdentityProvider.objects.filter(tenant__isnull=True, is_enabled=True).order_by("display_order", "name")
    )
    
    # Combine (tenant overrides first)
    return tenant_providers + platform_providers


@router.post("/tenant/{tenant_id}", response=IdentityProviderOut)
@require_auth(roles=["super-admin", "tenant-admin"])
def create_tenant_provider(request: AuthenticatedRequest, tenant_id: UUID, data: IdentityProviderCreate):
    """
    Create a tenant-specific identity provider.
    
    This overrides platform defaults for this tenant.
    """
    from somabrain.saas.models import Tenant
    tenant = get_object_or_404(Tenant, id=tenant_id)
    
    provider = IdentityProvider.objects.create(
        name=data.name,
        provider_type=data.provider_type,
        tenant=tenant,
        client_id=data.client_id,
        project_id=data.project_id,
        auth_uri=data.auth_uri,
        token_uri=data.token_uri,
        certs_url=data.certs_url,
        redirect_uris=data.redirect_uris,
        javascript_origins=data.javascript_origins,
        default_scopes=data.default_scopes,
        claim_mappings=data.claim_mappings,
        vault_secret_path=data.vault_secret_path,
        is_enabled=data.is_enabled,
        is_default=data.is_default,
        trust_email=data.trust_email,
        store_token=data.store_token,
        display_order=data.display_order,
    )
    
    # Audit log
    AuditLog.log(
        action="identity_provider.created",
        resource_type="IdentityProvider",
        resource_id=str(provider.id),
        actor_id=str(request.user_id),
        actor_type=ActorType.USER,
        tenant=tenant,
        details={"name": provider.name, "type": provider.provider_type, "scope": "tenant"},
    )
    
    return provider


# =============================================================================
# CONNECTION TEST
# =============================================================================

@router.post("/test-connection", response=TestConnectionResult)
@require_auth(roles=["super-admin", "tenant-admin"])
def test_provider_connection(request: AuthenticatedRequest, data: TestConnectionRequest):
    """
    Test connection to an identity provider.
    
    Validates that the OAuth configuration is correct and reachable.
    """
    import httpx
    
    try:
        # Get provider config
        if data.provider_id:
            provider = get_object_or_404(IdentityProvider, id=data.provider_id)
            auth_uri = provider.auth_uri
            token_uri = provider.token_uri
            certs_url = provider.certs_url
        elif data.provider_data:
            auth_uri = data.provider_data.auth_uri
            token_uri = data.provider_data.token_uri
            certs_url = data.provider_data.certs_url
        else:
            return TestConnectionResult(
                success=False,
                message="No provider specified"
            )
        
        results = {}
        
        # Test auth endpoint
        with httpx.Client(timeout=10) as client:
            try:
                resp = client.head(auth_uri, follow_redirects=True)
                results["auth_uri"] = {"status": resp.status_code, "reachable": resp.status_code < 500}
            except Exception as e:
                results["auth_uri"] = {"error": str(e), "reachable": False}
            
            # Test token endpoint
            try:
                # Just check if reachable (will fail auth but that's expected)
                resp = client.post(token_uri, data={})
                results["token_uri"] = {"status": resp.status_code, "reachable": True}
            except Exception as e:
                results["token_uri"] = {"error": str(e), "reachable": False}
            
            # Test certs URL if provided
            if certs_url:
                try:
                    resp = client.get(certs_url)
                    results["certs_url"] = {"status": resp.status_code, "reachable": resp.status_code == 200}
                except Exception as e:
                    results["certs_url"] = {"error": str(e), "reachable": False}
        
        # Determine overall success
        all_reachable = all(
            r.get("reachable", False) 
            for r in results.values()
        )
        
        return TestConnectionResult(
            success=all_reachable,
            message="All endpoints reachable" if all_reachable else "Some endpoints unreachable",
            details=results
        )
        
    except Exception as e:
        return TestConnectionResult(
            success=False,
            message=f"Connection test failed: {str(e)}"
        )


# =============================================================================
# PROVIDER TYPES INFO
# =============================================================================

@router.get("/types")
def list_provider_types(request):
    """
    List available provider types with their default configurations.
    
    Public endpoint for UI to know what fields each provider needs.
    """
    return {
        "google": {
            "name": "Google OAuth",
            "icon": "google",
            "default_auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "default_token_uri": "https://oauth2.googleapis.com/token",
            "default_certs_url": "https://www.googleapis.com/oauth2/v1/certs",
            "default_scopes": ["openid", "email", "profile"],
            "required_fields": ["client_id", "client_secret", "project_id"],
        },
        "facebook": {
            "name": "Facebook OAuth",
            "icon": "facebook",
            "default_auth_uri": "https://www.facebook.com/v18.0/dialog/oauth",
            "default_token_uri": "https://graph.facebook.com/v18.0/oauth/access_token",
            "default_scopes": ["email", "public_profile"],
            "required_fields": ["client_id", "client_secret"],
        },
        "github": {
            "name": "GitHub OAuth",
            "icon": "github",
            "default_auth_uri": "https://github.com/login/oauth/authorize",
            "default_token_uri": "https://github.com/login/oauth/access_token",
            "default_scopes": ["read:user", "user:email"],
            "required_fields": ["client_id", "client_secret"],
        },
        "keycloak": {
            "name": "Keycloak",
            "icon": "keycloak",
            "default_scopes": ["openid", "email", "profile"],
            "required_fields": ["client_id", "client_secret", "auth_uri", "token_uri"],
            "notes": "Set auth_uri and token_uri based on your Keycloak realm",
        },
        "oidc": {
            "name": "Generic OIDC",
            "icon": "oidc",
            "default_scopes": ["openid", "email", "profile"],
            "required_fields": ["client_id", "client_secret", "auth_uri", "token_uri"],
        },
    }
