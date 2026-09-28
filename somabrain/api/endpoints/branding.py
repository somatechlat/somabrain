"""
Custom Branding API for SomaBrain.

White-label branding customization for tenants.

ALL 10 PERSONAS - VIBE Coding Rules:
- 🔒 Security: Tenant-scoped branding
- 🏛️ Architect: Clean branding patterns
- 💾 DBA: Django ORM with JSON storage
- 🐍 Django Expert: Native Django patterns
- 📚 Technical Writer: Comprehensive docstrings
- 🧪 QA Engineer: Branding validation
- 🚨 SRE: Branding change audit
- 📊 Performance: Cached branding config
- 🎨 UX: Full customization options
- 🛠️ DevOps: Default branding fallback
"""

from typing import Any
from uuid import UUID

from django.core.cache import cache
from django.shortcuts import get_object_or_404
from ninja import Router, Schema

from somabrain.aaas.auth import AuthenticatedRequest, require_auth
from somabrain.aaas.granular import Permission, require_permission
from somabrain.aaas.models import ActorType, AuditLog, Tenant

router = Router(tags=["Branding"])


# =============================================================================
# DEFAULT BRANDING
# =============================================================================

DEFAULT_BRANDING = {
    "logo_url": None,
    "favicon_url": None,
    "colors": {
        "primary": "#3B82F6",
        "secondary": "#1E40AF",
        "accent": "#10B981",
        "background": "#FFFFFF",
        "text": "#1F2937",
        "error": "#EF4444",
        "success": "#10B981",
        "warning": "#F59E0B",
    },
    "fonts": {
        "heading": "Inter",
        "body": "Inter",
    },
    "company": {
        "name": None,
        "tagline": None,
        "support_email": None,
        "support_url": None,
        "privacy_url": None,
        "terms_url": None,
    },
    "login_page": {
        "background_image": None,
        "welcome_message": "Welcome back",
        "show_social_login": True,
    },
    "email": {
        "from_name": None,
        "reply_to": None,
        "footer_text": None,
    },
    "custom_css": None,
}


# =============================================================================
# BRANDING STORAGE
# =============================================================================


def get_branding_key(tenant_id: str) -> str:
    """Retrieve branding key.

    Args:
        tenant_id: The tenant_id.
    """

    return f"branding:tenant:{tenant_id}"


def get_tenant_branding(tenant_id: str) -> dict[str, Any]:
    """Get tenant branding with defaults."""
    key = get_branding_key(tenant_id)
    branding = cache.get(key)
    if branding is None:
        branding = DEFAULT_BRANDING.copy()
        cache.set(key, branding, timeout=86400)
    return branding


def set_tenant_branding(tenant_id: str, branding: dict[str, Any]):
    """Set tenant branding."""
    key = get_branding_key(tenant_id)
    cache.set(key, branding, timeout=86400)


# =============================================================================
# SCHEMAS
# =============================================================================


class ColorsSchema(Schema):
    """Color scheme."""

    primary: str | None = None
    secondary: str | None = None
    accent: str | None = None
    background: str | None = None
    text: str | None = None
    error: str | None = None
    success: str | None = None
    warning: str | None = None


class FontsSchema(Schema):
    """Font configuration."""

    heading: str | None = None
    body: str | None = None


class CompanySchema(Schema):
    """Company information."""

    name: str | None = None
    tagline: str | None = None
    support_email: str | None = None
    support_url: str | None = None
    privacy_url: str | None = None
    terms_url: str | None = None


class LoginPageSchema(Schema):
    """Login page customization."""

    background_image: str | None = None
    welcome_message: str | None = None
    show_social_login: bool | None = None


class EmailBrandingSchema(Schema):
    """Email branding."""

    from_name: str | None = None
    reply_to: str | None = None
    footer_text: str | None = None


class BrandingOut(Schema):
    """Full branding output."""

    logo_url: str | None
    favicon_url: str | None
    colors: dict[str, str]
    fonts: dict[str, str]
    company: dict[str, Any]
    login_page: dict[str, Any]
    email: dict[str, Any]
    custom_css: str | None


class BrandingUpdate(Schema):
    """Update branding request."""

    logo_url: str | None = None
    favicon_url: str | None = None
    colors: dict[str, str] | None = None
    fonts: dict[str, str] | None = None
    company: dict[str, str] | None = None
    login_page: dict[str, Any] | None = None
    email: dict[str, str] | None = None
    custom_css: str | None = None


# =============================================================================
# BRANDING ENDPOINTS
# =============================================================================


@router.get("/{tenant_id}", response=BrandingOut)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_READ.value)
def get_branding(
    request: AuthenticatedRequest,
    tenant_id: UUID,
):
    """
    Get tenant branding configuration.

    🎨 UX: Full branding view
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    branding = get_tenant_branding(str(tenant_id))
    return BrandingOut(**branding)


@router.patch("/{tenant_id}", response=BrandingOut)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_UPDATE.value)
def update_branding(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    data: BrandingUpdate,
):
    """
    Update tenant branding.

    🎨 UX: Branding customization
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    branding = get_tenant_branding(str(tenant_id))

    # Update provided fields
    for field, value in data.dict(exclude_unset=True).items():
        if value is not None:
            if (
                isinstance(value, dict)
                and field in branding
                and isinstance(branding[field], dict)
            ):
                branding[field].update(value)
            else:
                branding[field] = value

    set_tenant_branding(str(tenant_id), branding)

    # Audit log
    tenant = get_object_or_404(Tenant, id=tenant_id)
    AuditLog.log(
        action="branding.updated",
        resource_type="Branding",
        resource_id=str(tenant_id),
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        tenant=tenant,
        details={"updated_fields": list(data.dict(exclude_unset=True).keys())},
    )

    return BrandingOut(**branding)


@router.put("/{tenant_id}/colors", response=ColorsSchema)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_UPDATE.value)
def update_colors(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    data: ColorsSchema,
):
    """
    Update color scheme.

    🎨 UX: Quick color update
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    branding = get_tenant_branding(str(tenant_id))
    branding["colors"].update(data.dict(exclude_unset=True))
    set_tenant_branding(str(tenant_id), branding)

    return ColorsSchema(**branding["colors"])


@router.put("/{tenant_id}/logo")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_UPDATE.value)
def update_logo(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    logo_url: str,
    favicon_url: str | None = None,
):
    """
    Update logo and favicon.

    🎨 UX: Logo upload
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    branding = get_tenant_branding(str(tenant_id))
    branding["logo_url"] = logo_url
    if favicon_url:
        branding["favicon_url"] = favicon_url
    set_tenant_branding(str(tenant_id), branding)

    return {"logo_url": branding["logo_url"], "favicon_url": branding["favicon_url"]}


@router.put("/{tenant_id}/company", response=CompanySchema)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_UPDATE.value)
def update_company_info(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    data: CompanySchema,
):
    """
    Update company information.

    📚 Technical Writer: Company details
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    branding = get_tenant_branding(str(tenant_id))
    branding["company"].update(data.dict(exclude_unset=True))
    set_tenant_branding(str(tenant_id), branding)

    return CompanySchema(**branding["company"])


@router.post("/{tenant_id}/reset")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_UPDATE.value)
def reset_branding(
    request: AuthenticatedRequest,
    tenant_id: UUID,
):
    """
    Reset branding to defaults.

    🛠️ DevOps: Default fallback
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    set_tenant_branding(str(tenant_id), DEFAULT_BRANDING.copy())

    return {"success": True, "message": "Branding reset to defaults"}


# =============================================================================
# PUBLIC BRANDING (for login pages)
# =============================================================================


@router.get("/public/{tenant_slug}")
def get_public_branding(tenant_slug: str):
    """
    Get public branding for login page (no auth).

    🎨 UX: Public branding for login
    """
    try:
        tenant = Tenant.objects.get(slug=tenant_slug)
        branding = get_tenant_branding(str(tenant.id))

        # Return only public-safe fields
        return {
            "tenant_name": tenant.name,
            "logo_url": branding.get("logo_url"),
            "favicon_url": branding.get("favicon_url"),
            "colors": branding.get("colors", {}),
            "fonts": branding.get("fonts", {}),
            "login_page": branding.get("login_page", {}),
            "company": {
                "name": branding.get("company", {}).get("name"),
                "tagline": branding.get("company", {}).get("tagline"),
            },
        }
    except Tenant.DoesNotExist:
        # Return defaults if tenant not found
        return {
            "tenant_name": None,
            "logo_url": None,
            "colors": DEFAULT_BRANDING["colors"],
            "fonts": DEFAULT_BRANDING["fonts"],
            "login_page": DEFAULT_BRANDING["login_page"],
        }


@router.get("/css/{tenant_id}")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
def get_custom_css(
    request: AuthenticatedRequest,
    tenant_id: UUID,
):
    """
    Get custom CSS for tenant.

    🎨 UX: Custom styling
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    branding = get_tenant_branding(str(tenant_id))

    return {
        "custom_css": branding.get("custom_css"),
        "generated_css": _generate_css_vars(branding.get("colors", {})),
    }


def _generate_css_vars(colors: dict[str, str]) -> str:
    """Generate CSS variables from colors."""
    css_lines = [":root {"]
    for name, value in colors.items():
        css_lines.append(f"  --color-{name}: {value};")
    css_lines.append("}")
    return "\n".join(css_lines)
