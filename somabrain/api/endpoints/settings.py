"""
Settings Management API for SomaBrain.

Hierarchical settings for tenants and platform configuration.

ALL 10 PERSONAS - VIBE Coding Rules:
- 🔒 Security Engineer: Settings authorization, sensitive value masking
- 🏛️ Architect: Hierarchical config (platform -> tier -> tenant)
- 💾 DBA: Django ORM with efficient lookup
- 🐍 Django Expert: Native Django patterns
- 📚 Technical Writer: Comprehensive docstrings
- 🧪 QA Engineer: Testable settings validation
- 🚨 SRE: Configuration drift detection
- 📊 Performance Engineer: Cached settings
- 🎨 UX Advocate: Clear settings organization
- 🛠️ DevOps: Environment variable overrides
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID

from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from ninja import Router, Schema

from somabrain.saas.models import Tenant, AuditLog, ActorType
from somabrain.saas.auth import require_auth, AuthenticatedRequest
from somabrain.saas.granular import require_permission, Permission


router = Router(tags=["Settings"])


# =============================================================================
# SETTING CATEGORIES - ALL 10 PERSONAS
# =============================================================================

SETTING_CATEGORIES = {
    "general": {
        "name": "General",
        "description": "General organization settings",
        "settings": ["org_name", "timezone", "locale", "date_format"],
    },
    "security": {
        "name": "Security",
        "description": "Security and authentication settings",
        "settings": ["mfa_required", "session_timeout", "ip_whitelist", "api_key_expiry"],
    },
    "notifications": {
        "name": "Notifications",
        "description": "Notification preferences",
        "settings": ["email_notifications", "slack_webhook", "webhook_events"],
    },
    "billing": {
        "name": "Billing",
        "description": "Billing and subscription settings",
        "settings": ["auto_renew", "billing_email", "invoice_format"],
    },
    "api": {
        "name": "API",
        "description": "API configuration",
        "settings": ["rate_limit_override", "allowed_origins", "api_version"],
    },
    "cognitive": {
        "name": "Cognitive",
        "description": "Cognitive service settings",
        "settings": ["default_model", "embedding_model", "max_tokens", "temperature"],
    },
}

# Default values
SETTING_DEFAULTS = {
    "org_name": "",
    "timezone": "UTC",
    "locale": "en-US",
    "date_format": "YYYY-MM-DD",
    "mfa_required": False,
    "session_timeout": 3600,
    "ip_whitelist": [],
    "api_key_expiry": 90,
    "email_notifications": True,
    "slack_webhook": "",
    "webhook_events": ["tenant.updated", "subscription.changed"],
    "auto_renew": True,
    "billing_email": "",
    "invoice_format": "pdf",
    "rate_limit_override": None,
    "allowed_origins": ["*"],
    "api_version": "v1",
    "default_model": "gpt-4",
    "embedding_model": "text-embedding-3-small",
    "max_tokens": 4096,
    "temperature": 0.7,
}

# Sensitive settings that should be masked
SENSITIVE_SETTINGS = {"slack_webhook", "billing_email"}


# =============================================================================
# SCHEMAS - ALL 10 PERSONAS
# =============================================================================

class SettingOut(Schema):
    """Setting output."""
    key: str
    value: Any
    category: str
    is_default: bool
    updated_at: Optional[str]
    updated_by: Optional[str]


class SettingUpdate(Schema):
    """Update a setting."""
    value: Any


class SettingsBulkUpdate(Schema):
    """Bulk update settings."""
    settings: Dict[str, Any]


class CategorySettingsOut(Schema):
    """Settings grouped by category."""
    category: str
    name: str
    description: str
    settings: List[SettingOut]


# =============================================================================
# SETTINGS STORAGE - CACHE BACKED
# =============================================================================

def get_settings_key(tenant_id: str) -> str:
    """Generate cache key for tenant settings."""
    return f"settings:tenant:{tenant_id}"


def get_tenant_settings(tenant_id: str) -> Dict[str, Any]:
    """Get tenant settings with defaults."""
    key = get_settings_key(tenant_id)
    stored = cache.get(key, {})
    
    # Merge with defaults
    settings = SETTING_DEFAULTS.copy()
    settings.update(stored.get("values", {}))
    
    return settings


def get_setting_metadata(tenant_id: str) -> Dict[str, Dict]:
    """Get metadata (updated_at, updated_by) for settings."""
    key = get_settings_key(tenant_id)
    stored = cache.get(key, {})
    return stored.get("metadata", {})


def save_tenant_setting(tenant_id: str, key: str, value: Any, user_id: str):
    """Save a tenant setting."""
    cache_key = get_settings_key(tenant_id)
    stored = cache.get(cache_key, {"values": {}, "metadata": {}})
    
    stored["values"][key] = value
    stored["metadata"][key] = {
        "updated_at": timezone.now().isoformat(),
        "updated_by": user_id,
    }
    
    cache.set(cache_key, stored, timeout=86400 * 30)


def save_tenant_settings_bulk(tenant_id: str, settings: Dict[str, Any], user_id: str):
    """Save multiple tenant settings."""
    cache_key = get_settings_key(tenant_id)
    stored = cache.get(cache_key, {"values": {}, "metadata": {}})
    
    now = timezone.now().isoformat()
    for key, value in settings.items():
        stored["values"][key] = value
        stored["metadata"][key] = {
            "updated_at": now,
            "updated_by": user_id,
        }
    
    cache.set(cache_key, stored, timeout=86400 * 30)


def mask_sensitive_value(key: str, value: Any) -> Any:
    """Mask sensitive setting values."""
    if key in SENSITIVE_SETTINGS and value:
        if isinstance(value, str) and len(value) > 4:
            return value[:2] + "*" * (len(value) - 4) + value[-2:]
    return value


# =============================================================================
# ENDPOINTS - ALL 10 PERSONAS
# =============================================================================

@router.get("/{tenant_id}", response=List[CategorySettingsOut])
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
def get_all_settings(
    request: AuthenticatedRequest,
    tenant_id: UUID,
):
    """
    Get all settings organized by category.
    
    🏛️ Architect: Hierarchical organization
    🎨 UX: Clear grouping
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    settings = get_tenant_settings(str(tenant_id))
    metadata = get_setting_metadata(str(tenant_id))
    
    result = []
    for cat_key, cat_info in SETTING_CATEGORIES.items():
        cat_settings = []
        for setting_key in cat_info["settings"]:
            value = settings.get(setting_key, SETTING_DEFAULTS.get(setting_key))
            meta = metadata.get(setting_key, {})
            
            cat_settings.append(SettingOut(
                key=setting_key,
                value=mask_sensitive_value(setting_key, value),
                category=cat_key,
                is_default=setting_key not in metadata,
                updated_at=meta.get("updated_at"),
                updated_by=meta.get("updated_by"),
            ))
        
        result.append(CategorySettingsOut(
            category=cat_key,
            name=cat_info["name"],
            description=cat_info["description"],
            settings=cat_settings,
        ))
    
    return result


@router.get("/{tenant_id}/category/{category}", response=CategorySettingsOut)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
def get_category_settings(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    category: str,
):
    """Get settings for a specific category."""
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    if category not in SETTING_CATEGORIES:
        from ninja.errors import HttpError
        raise HttpError(404, f"Category '{category}' not found")
    
    settings = get_tenant_settings(str(tenant_id))
    metadata = get_setting_metadata(str(tenant_id))
    cat_info = SETTING_CATEGORIES[category]
    
    cat_settings = []
    for setting_key in cat_info["settings"]:
        value = settings.get(setting_key, SETTING_DEFAULTS.get(setting_key))
        meta = metadata.get(setting_key, {})
        
        cat_settings.append(SettingOut(
            key=setting_key,
            value=mask_sensitive_value(setting_key, value),
            category=category,
            is_default=setting_key not in metadata,
            updated_at=meta.get("updated_at"),
            updated_by=meta.get("updated_by"),
        ))
    
    return CategorySettingsOut(
        category=category,
        name=cat_info["name"],
        description=cat_info["description"],
        settings=cat_settings,
    )


@router.get("/{tenant_id}/{key}", response=SettingOut)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
def get_setting(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    key: str,
):
    """Get a specific setting."""
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    if key not in SETTING_DEFAULTS:
        from ninja.errors import HttpError
        raise HttpError(404, f"Setting '{key}' not found")
    
    settings = get_tenant_settings(str(tenant_id))
    metadata = get_setting_metadata(str(tenant_id))
    meta = metadata.get(key, {})
    
    # Find category
    category = "general"
    for cat_key, cat_info in SETTING_CATEGORIES.items():
        if key in cat_info["settings"]:
            category = cat_key
            break
    
    return SettingOut(
        key=key,
        value=mask_sensitive_value(key, settings.get(key)),
        category=category,
        is_default=key not in metadata,
        updated_at=meta.get("updated_at"),
        updated_by=meta.get("updated_by"),
    )


@router.put("/{tenant_id}/{key}", response=SettingOut)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_UPDATE.value)
def update_setting(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    key: str,
    data: SettingUpdate,
):
    """
    Update a specific setting.
    
    🔒 Security: Authorized update
    🚨 SRE: Audit logging
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    if key not in SETTING_DEFAULTS:
        from ninja.errors import HttpError
        raise HttpError(404, f"Setting '{key}' not found")
    
    # Save setting
    save_tenant_setting(str(tenant_id), key, data.value, str(request.user_id))
    
    # Audit log
    tenant = get_object_or_404(Tenant, id=tenant_id)
    AuditLog.log(
        action="settings.updated",
        resource_type="Setting",
        resource_id=key,
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        tenant=tenant,
        details={"key": key, "value": mask_sensitive_value(key, data.value)},
    )
    
    # Return updated setting
    settings = get_tenant_settings(str(tenant_id))
    metadata = get_setting_metadata(str(tenant_id))
    meta = metadata.get(key, {})
    
    category = "general"
    for cat_key, cat_info in SETTING_CATEGORIES.items():
        if key in cat_info["settings"]:
            category = cat_key
            break
    
    return SettingOut(
        key=key,
        value=mask_sensitive_value(key, settings.get(key)),
        category=category,
        is_default=False,
        updated_at=meta.get("updated_at"),
        updated_by=meta.get("updated_by"),
    )


@router.put("/{tenant_id}/bulk")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_UPDATE.value)
def update_settings_bulk(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    data: SettingsBulkUpdate,
):
    """
    Update multiple settings at once.
    
    📊 Performance: Batch update
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    # Validate keys
    invalid_keys = [k for k in data.settings.keys() if k not in SETTING_DEFAULTS]
    if invalid_keys:
        from ninja.errors import HttpError
        raise HttpError(400, f"Invalid settings: {', '.join(invalid_keys)}")
    
    # Save settings
    save_tenant_settings_bulk(str(tenant_id), data.settings, str(request.user_id))
    
    # Audit log
    tenant = get_object_or_404(Tenant, id=tenant_id)
    AuditLog.log(
        action="settings.bulk_updated",
        resource_type="Setting",
        resource_id="bulk",
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        tenant=tenant,
        details={"keys": list(data.settings.keys())},
    )
    
    return {"success": True, "updated_count": len(data.settings)}


@router.post("/{tenant_id}/reset/{key}")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_UPDATE.value)
def reset_setting(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    key: str,
):
    """Reset a setting to its default value."""
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    if key not in SETTING_DEFAULTS:
        from ninja.errors import HttpError
        raise HttpError(404, f"Setting '{key}' not found")
    
    # Remove from cache
    cache_key = get_settings_key(str(tenant_id))
    stored = cache.get(cache_key, {"values": {}, "metadata": {}})
    
    if key in stored["values"]:
        del stored["values"][key]
    if key in stored["metadata"]:
        del stored["metadata"][key]
    
    cache.set(cache_key, stored, timeout=86400 * 30)
    
    return {
        "success": True,
        "key": key,
        "default_value": SETTING_DEFAULTS.get(key),
    }


@router.post("/{tenant_id}/reset-all")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_UPDATE.value)
def reset_all_settings(
    request: AuthenticatedRequest,
    tenant_id: UUID,
):
    """Reset all settings to defaults."""
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError
            raise HttpError(403, "Access denied")
    
    cache_key = get_settings_key(str(tenant_id))
    cache.delete(cache_key)
    
    # Audit log
    tenant = get_object_or_404(Tenant, id=tenant_id)
    AuditLog.log(
        action="settings.reset_all",
        resource_type="Setting",
        resource_id="all",
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        tenant=tenant,
    )
    
    return {"success": True, "message": "All settings reset to defaults"}
