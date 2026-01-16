"""
Feature Flags API for SomaBrain.

Dynamic feature flag management for tenants and platform.

ALL 10 PERSONAS per VIBE Coding Rules:
- 🔒 Security: Tenant isolation
- 🏛️ Architect: Clean flag patterns
- 💾 DBA: Django ORM
- 🐍 Django: Native patterns
- 📚 Docs: Comprehensive docstrings
- 🧪 QA: Testable interfaces
- 🚨 SRE: Gradual rollouts
- 📊 Perf: Cached lookups
- 🎨 UX: Clear flag states
- 🛠️ DevOps: Environment overrides
"""

from typing import List, Optional, Dict
from uuid import UUID

from django.utils import timezone
from django.core.cache import cache
from ninja import Router, Schema

from somabrain.saas.models import Tenant, AuditLog, ActorType
from somabrain.saas.auth import require_auth, AuthenticatedRequest
from somabrain.saas.granular import require_permission, Permission


router = Router(tags=["Feature Flags"])


# =============================================================================
# SCHEMAS
# =============================================================================


class FeatureFlagOut(Schema):
    """Feature flag output."""

    key: str
    name: str
    description: Optional[str]
    enabled: bool
    rollout_percentage: int
    created_at: str
    updated_at: str


class FeatureFlagCreate(Schema):
    """Create feature flag."""

    key: str
    name: str
    description: Optional[str] = None
    enabled: bool = False
    rollout_percentage: int = 0


class FeatureFlagUpdate(Schema):
    """Update feature flag."""

    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    rollout_percentage: Optional[int] = None


class TenantFlagOverride(Schema):
    """Tenant-specific flag override."""

    flag_key: str
    enabled: bool
    reason: Optional[str] = None


class FlagCheckResult(Schema):
    """Result of flag check."""

    flag_key: str
    enabled: bool
    source: str  # default, tenant_override, rollout


# =============================================================================
# IN-MEMORY FLAG STORE (would be database model in production)
# =============================================================================

# Default flags - in production, this would be a Django model
DEFAULT_FLAGS = {
    "new_dashboard": {
        "key": "new_dashboard",
        "name": "New Dashboard UI",
        "description": "Enable the redesigned dashboard interface",
        "enabled": False,
        "rollout_percentage": 0,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    },
    "advanced_analytics": {
        "key": "advanced_analytics",
        "name": "Advanced Analytics",
        "description": "Enable advanced usage analytics features",
        "enabled": True,
        "rollout_percentage": 100,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    },
    "webhooks_v2": {
        "key": "webhooks_v2",
        "name": "Webhooks V2",
        "description": "Enable new webhook delivery system",
        "enabled": False,
        "rollout_percentage": 25,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    },
    "ai_suggestions": {
        "key": "ai_suggestions",
        "name": "AI Suggestions",
        "description": "Enable AI-powered suggestions",
        "enabled": True,
        "rollout_percentage": 50,
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z",
    },
}


def get_all_flags() -> Dict[str, dict]:
    """Get all flags from cache or defaults."""
    cached = cache.get("feature_flags")
    if cached:
        return cached
    return DEFAULT_FLAGS.copy()


def get_flag(key: str) -> Optional[dict]:
    """Get a single flag."""
    flags = get_all_flags()
    return flags.get(key)


def set_flag(key: str, flag_data: dict):
    """Update a flag."""
    flags = get_all_flags()
    flags[key] = flag_data
    cache.set("feature_flags", flags, timeout=3600)


def get_tenant_overrides(tenant_id: str) -> Dict[str, bool]:
    """Get tenant-specific flag overrides."""
    return cache.get(f"feature_flags:tenant:{tenant_id}", {})


def set_tenant_override(tenant_id: str, flag_key: str, enabled: bool):
    """Set tenant-specific override."""
    overrides = get_tenant_overrides(tenant_id)
    overrides[flag_key] = enabled
    cache.set(f"feature_flags:tenant:{tenant_id}", overrides, timeout=3600)


# =============================================================================
# FLAG EVALUATION
# =============================================================================


def evaluate_flag(flag_key: str, tenant_id: Optional[str] = None) -> tuple:
    """
    Evaluate if a flag is enabled for a given context.

    Returns (enabled: bool, source: str)
    """
    flag = get_flag(flag_key)
    if not flag:
        return False, "not_found"

    # Check tenant override first
    if tenant_id:
        overrides = get_tenant_overrides(tenant_id)
        if flag_key in overrides:
            return overrides[flag_key], "tenant_override"

    # Check if globally enabled
    if flag.get("enabled"):
        return True, "default"

    # Check rollout percentage
    rollout = flag.get("rollout_percentage", 0)
    if rollout > 0 and tenant_id:
        # Simple hash-based rollout
        import hashlib

        hash_input = f"{flag_key}:{tenant_id}"
        hash_value = int(hashlib.md5(hash_input.encode()).hexdigest()[:8], 16)
        bucket = hash_value % 100
        if bucket < rollout:
            return True, "rollout"

    return False, "default"


# =============================================================================
# ENDPOINTS
# =============================================================================


@router.get("/flags", response=List[FeatureFlagOut])
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
def list_feature_flags(request: AuthenticatedRequest):
    """List all feature flags."""
    flags = get_all_flags()
    return [FeatureFlagOut(**flag) for flag in flags.values()]


@router.get("/flags/{flag_key}", response=FeatureFlagOut)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
def get_feature_flag(request: AuthenticatedRequest, flag_key: str):
    """Get a specific feature flag."""
    flag = get_flag(flag_key)
    if not flag:
        from ninja.errors import HttpError

        raise HttpError(404, f"Flag '{flag_key}' not found")
    return FeatureFlagOut(**flag)


@router.post("/flags", response=FeatureFlagOut)
@require_auth(roles=["super-admin"])
@require_permission(Permission.PLATFORM_MANAGE.value)
def create_feature_flag(request: AuthenticatedRequest, data: FeatureFlagCreate):
    """Create a new feature flag (super admin only)."""
    existing = get_flag(data.key)
    if existing:
        from ninja.errors import HttpError

        raise HttpError(400, f"Flag '{data.key}' already exists")

    now = timezone.now().isoformat()
    flag_data = {
        "key": data.key,
        "name": data.name,
        "description": data.description,
        "enabled": data.enabled,
        "rollout_percentage": data.rollout_percentage,
        "created_at": now,
        "updated_at": now,
    }
    set_flag(data.key, flag_data)

    # Audit log
    AuditLog.log(
        action="feature_flag.created",
        resource_type="FeatureFlag",
        resource_id=data.key,
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        details={"name": data.name, "enabled": data.enabled},
    )

    return FeatureFlagOut(**flag_data)


@router.patch("/flags/{flag_key}", response=FeatureFlagOut)
@require_auth(roles=["super-admin"])
@require_permission(Permission.PLATFORM_MANAGE.value)
def update_feature_flag(request: AuthenticatedRequest, flag_key: str, data: FeatureFlagUpdate):
    """Update a feature flag (super admin only)."""
    flag = get_flag(flag_key)
    if not flag:
        from ninja.errors import HttpError

        raise HttpError(404, f"Flag '{flag_key}' not found")

    if data.name is not None:
        flag["name"] = data.name
    if data.description is not None:
        flag["description"] = data.description
    if data.enabled is not None:
        flag["enabled"] = data.enabled
    if data.rollout_percentage is not None:
        flag["rollout_percentage"] = data.rollout_percentage

    flag["updated_at"] = timezone.now().isoformat()
    set_flag(flag_key, flag)

    # Audit log
    AuditLog.log(
        action="feature_flag.updated",
        resource_type="FeatureFlag",
        resource_id=flag_key,
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        details={"enabled": flag["enabled"], "rollout": flag["rollout_percentage"]},
    )

    return FeatureFlagOut(**flag)


@router.delete("/flags/{flag_key}")
@require_auth(roles=["super-admin"])
@require_permission(Permission.PLATFORM_MANAGE.value)
def delete_feature_flag(request: AuthenticatedRequest, flag_key: str):
    """Delete a feature flag (super admin only)."""
    flag = get_flag(flag_key)
    if not flag:
        from ninja.errors import HttpError

        raise HttpError(404, f"Flag '{flag_key}' not found")

    flags = get_all_flags()
    del flags[flag_key]
    cache.set("feature_flags", flags, timeout=3600)

    return {"success": True}


# =============================================================================
# TENANT OVERRIDES
# =============================================================================


@router.post("/{tenant_id}/overrides")
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.TENANTS_UPDATE.value)
def set_tenant_flag_override(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    data: TenantFlagOverride,
):
    """Set a tenant-specific flag override."""
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    set_tenant_override(str(tenant_id), data.flag_key, data.enabled)

    # Audit log
    from django.shortcuts import get_object_or_404

    tenant = get_object_or_404(Tenant, id=tenant_id)
    AuditLog.log(
        action="feature_flag.override_set",
        resource_type="FeatureFlag",
        resource_id=data.flag_key,
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        tenant=tenant,
        details={"enabled": data.enabled, "reason": data.reason},
    )

    return {"success": True, "flag_key": data.flag_key, "enabled": data.enabled}


@router.get("/{tenant_id}/check/{flag_key}", response=FlagCheckResult)
@require_auth(roles=["super-admin", "tenant-admin", "tenant-user"], any_role=True)
def check_flag(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    flag_key: str,
):
    """Check if a flag is enabled for a tenant."""
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    enabled, source = evaluate_flag(flag_key, str(tenant_id))

    return FlagCheckResult(
        flag_key=flag_key,
        enabled=enabled,
        source=source,
    )


@router.post("/{tenant_id}/check-bulk")
@require_auth(roles=["super-admin", "tenant-admin", "tenant-user"], any_role=True)
def check_flags_bulk(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    flag_keys: List[str],
):
    """Check multiple flags at once."""
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    results = {}
    for key in flag_keys:
        enabled, source = evaluate_flag(key, str(tenant_id))
        results[key] = {"enabled": enabled, "source": source}

    return {"flags": results}
