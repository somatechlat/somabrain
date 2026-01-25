"""
SSO Identity Provider API Endpoints.

Django Ninja API for enterprise SSO configuration.

ALL 10 PERSONAS - VIBE Coding Rules:
- 🔒 Security: Secure SSO configuration
- 🏛️ Architect: Clean IdP patterns
- 💾 DBA: Django ORM with encrypted secrets
- 🐍 Django Expert: Native Django patterns
- 📚 Technical Writer: Comprehensive docstrings
- 🧪 QA Engineer: SSO flow validation
- 🚨 SRE: SSO monitoring and alerts
- 📊 Performance: Cached IdP config
- 🎨 UX: SSO onboarding flow
- 🛠️ DevOps: IdP provisioning
"""

import time
from typing import List
from uuid import UUID

import httpx
from django.core.cache import cache
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ninja import Router
from ninja.errors import HttpError

from somabrain.aaas.auth import AuthenticatedRequest, require_auth
from somabrain.aaas.granular import Permission, require_permission
from somabrain.aaas.models import ActorType, AuditLog, Tenant

from .schemas import IdPCreate, IdPDetailOut, IdPOut, IdPStatus, IdPType, IdPUpdate, SSOSettings
from .storage import create_idp, delete_idp, get_idp, get_tenant_idps, mask_sensitive_config, update_idp

router = Router(tags=["SSO"])


# =============================================================================
# IDP CRUD ENDPOINTS
# =============================================================================


@router.get("/{tenant_id}/providers", response=List[IdPOut])
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.IDP_LIST.value)
def list_identity_providers(request: AuthenticatedRequest, tenant_id: UUID):
    """List all identity providers for a tenant."""
    if not request.is_super_admin and str(request.tenant_id) != str(tenant_id):
        raise HttpError(403, "Access denied")
    idps = get_tenant_idps(str(tenant_id))
    return [IdPOut(id=idp["id"], name=idp["name"], type=idp["type"], status=idp["status"],
        created_at=idp["created_at"], last_verified_at=idp.get("last_verified_at"),
        login_count=idp.get("login_count", 0), error_count=idp.get("error_count", 0)) for idp in idps]


@router.post("/{tenant_id}/providers", response=IdPDetailOut)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.IDP_CREATE.value)
def create_identity_provider(request: AuthenticatedRequest, tenant_id: UUID, data: IdPCreate):
    """Create a new identity provider."""
    if not request.is_super_admin and str(request.tenant_id) != str(tenant_id):
        raise HttpError(403, "Access denied")
    if data.type not in [t.value for t in IdPType]:
        raise HttpError(400, f"Invalid IdP type: {data.type}")
    idp = create_idp(tenant_id=str(tenant_id), name=data.name, provider_type=data.type,
        config=data.config, created_by=str(request.user_id))
    tenant = get_object_or_404(Tenant, id=tenant_id)
    AuditLog.log(action="idp.created", resource_type="IdentityProvider", resource_id=idp["id"],
        actor_id=str(request.user_id), actor_type=ActorType.ADMIN, tenant=tenant,
        details={"name": data.name, "type": data.type})
    safe_config = mask_sensitive_config(idp["config"])
    return IdPDetailOut(id=idp["id"], name=idp["name"], type=idp["type"], status=idp["status"],
        config=safe_config, created_at=idp["created_at"], created_by=idp.get("created_by"),
        last_verified_at=idp.get("last_verified_at"), login_count=idp.get("login_count", 0),
        error_count=idp.get("error_count", 0), last_error=idp.get("last_error"))


@router.get("/{tenant_id}/providers/{idp_id}", response=IdPDetailOut)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.IDP_READ.value)
def get_identity_provider(request: AuthenticatedRequest, tenant_id: UUID, idp_id: str):
    """Get identity provider details."""
    if not request.is_super_admin and str(request.tenant_id) != str(tenant_id):
        raise HttpError(403, "Access denied")
    idp = get_idp(idp_id)
    if not idp or idp["tenant_id"] != str(tenant_id):
        raise HttpError(404, "Identity provider not found")
    safe_config = mask_sensitive_config(idp["config"])
    return IdPDetailOut(id=idp["id"], name=idp["name"], type=idp["type"], status=idp["status"],
        config=safe_config, created_at=idp["created_at"], created_by=idp.get("created_by"),
        last_verified_at=idp.get("last_verified_at"), login_count=idp.get("login_count", 0),
        error_count=idp.get("error_count", 0), last_error=idp.get("last_error"))


@router.patch("/{tenant_id}/providers/{idp_id}", response=IdPDetailOut)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.IDP_UPDATE.value)
def update_identity_provider(request: AuthenticatedRequest, tenant_id: UUID, idp_id: str, data: IdPUpdate):
    """Update identity provider."""
    if not request.is_super_admin and str(request.tenant_id) != str(tenant_id):
        raise HttpError(403, "Access denied")
    idp = get_idp(idp_id)
    if not idp or idp["tenant_id"] != str(tenant_id):
        raise HttpError(404, "Identity provider not found")
    if data.name is not None:
        idp["name"] = data.name
    if data.config is not None:
        idp["config"].update(data.config)
    if data.status is not None:
        idp["status"] = data.status
    update_idp(idp_id, **idp)
    safe_config = mask_sensitive_config(idp["config"])
    return IdPDetailOut(id=idp["id"], name=idp["name"], type=idp["type"], status=idp["status"],
        config=safe_config, created_at=idp["created_at"], created_by=idp.get("created_by"),
        last_verified_at=idp.get("last_verified_at"), login_count=idp.get("login_count", 0),
        error_count=idp.get("error_count", 0), last_error=idp.get("last_error"))


@router.delete("/{tenant_id}/providers/{idp_id}")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.IDP_DELETE.value)
def delete_identity_provider(request: AuthenticatedRequest, tenant_id: UUID, idp_id: str):
    """Delete identity provider."""
    if not request.is_super_admin and str(request.tenant_id) != str(tenant_id):
        raise HttpError(403, "Access denied")
    idp = get_idp(idp_id)
    if not idp or idp["tenant_id"] != str(tenant_id):
        raise HttpError(404, "Identity provider not found")
    delete_idp(idp_id, str(tenant_id))
    return {"success": True, "deleted": idp_id}


# =============================================================================
# SSO CONFIGURATION
# =============================================================================


@router.get("/{tenant_id}/settings", response=SSOSettings)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.IDP_READ.value)
def get_sso_settings(request: AuthenticatedRequest, tenant_id: UUID):
    """Get SSO settings for tenant."""
    if not request.is_super_admin and str(request.tenant_id) != str(tenant_id):
        raise HttpError(403, "Access denied")
    settings = cache.get(f"sso_settings:{tenant_id}", {})
    return SSOSettings(**settings)


@router.put("/{tenant_id}/settings", response=SSOSettings)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.IDP_UPDATE.value)
def update_sso_settings(request: AuthenticatedRequest, tenant_id: UUID, data: SSOSettings):
    """Update SSO settings."""
    if not request.is_super_admin and str(request.tenant_id) != str(tenant_id):
        raise HttpError(403, "Access denied")
    cache.set(f"sso_settings:{tenant_id}", data.dict(), timeout=86400 * 30)
    tenant = get_object_or_404(Tenant, id=tenant_id)
    AuditLog.log(action="sso.settings_updated", resource_type="SSOSettings", resource_id=str(tenant_id),
        actor_id=str(request.user_id), actor_type=ActorType.ADMIN, tenant=tenant, details=data.dict())
    return data


# =============================================================================
# IDP TESTING
# =============================================================================


@router.post("/{tenant_id}/providers/{idp_id}/test")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.IDP_TEST.value)
def test_identity_provider(request: AuthenticatedRequest, tenant_id: UUID, idp_id: str):
    """Test identity provider configuration."""
    if not request.is_super_admin and str(request.tenant_id) != str(tenant_id):
        raise HttpError(403, "Access denied")
    idp = get_idp(idp_id)
    if not idp or idp["tenant_id"] != str(tenant_id):
        raise HttpError(404, "Identity provider not found")

    test_result = {"success": False, "message": "", "details": {}}
    start_time = time.time()
    config = idp.get("config", {})
    idp_type = idp.get("type")

    try:
        if idp_type == "oidc":
            issuer_url = config.get("issuer_url", "")
            if issuer_url:
                with httpx.Client(timeout=10.0) as client:
                    well_known = f"{issuer_url.rstrip('/')}/.well-known/openid-configuration"
                    response = client.get(well_known)
                    if response.status_code == 200:
                        test_result["success"] = True
                        test_result["message"] = "OIDC configuration verified"
                        test_result["details"]["well_known"] = "OK"
                    else:
                        test_result["message"] = f"OIDC endpoint returned {response.status_code}"
        elif idp_type == "saml":
            sso_url = config.get("sso_url", "")
            if sso_url:
                with httpx.Client(timeout=10.0) as client:
                    response = client.head(sso_url)
                    test_result["success"] = response.status_code < 500
                    test_result["message"] = f"SAML endpoint status: {response.status_code}"
        else:
            test_result["success"] = True
            test_result["message"] = f"Configuration saved for {idp_type}"
        test_result["details"]["response_time_ms"] = int((time.time() - start_time) * 1000)
    except httpx.RequestError as e:
        test_result["message"] = f"Connection failed: {str(e)}"
        test_result["details"]["error"] = str(e)

    if test_result["success"]:
        update_idp(idp_id, last_verified_at=timezone.now().isoformat())
    else:
        update_idp(idp_id, last_error=test_result["message"], error_count=idp.get("error_count", 0) + 1)
    return test_result


@router.post("/{tenant_id}/providers/{idp_id}/activate")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.IDP_UPDATE.value)
def activate_identity_provider(request: AuthenticatedRequest, tenant_id: UUID, idp_id: str):
    """Activate identity provider."""
    if not request.is_super_admin and str(request.tenant_id) != str(tenant_id):
        raise HttpError(403, "Access denied")
    idp = get_idp(idp_id)
    if not idp or idp["tenant_id"] != str(tenant_id):
        raise HttpError(404, "Identity provider not found")
    update_idp(idp_id, status=IdPStatus.ACTIVE)
    return {"success": True, "status": "active"}
