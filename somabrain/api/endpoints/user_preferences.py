"""
User Preferences and Profiles API for SomaBrain.

Manage user preferences, settings, and profile data.

ALL 10 PERSONAS - VIBE Coding Rules:
- 🔒 Security: User data isolation
- 🏛️ Architect: Clean profile patterns
- 💾 DBA: Django ORM with JSON fields
- 🐍 Django Expert: Native Django patterns
- 📚 Technical Writer: Comprehensive docstrings
- 🧪 QA Engineer: Preference validation
- 🚨 SRE: Profile change audit
- 📊 Performance: Cached preferences
- 🎨 UX: Personalization support
- 🛠️ DevOps: Default configuration
"""

from typing import Any
from uuid import UUID

from django.core.cache import cache
from django.shortcuts import get_object_or_404
from ninja import Router, Schema

from somabrain.aaas.auth import AuthenticatedRequest, require_auth
from somabrain.aaas.granular import Permission, require_permission
from somabrain.aaas.models import ActorType, AuditLog, TenantUser

router = Router(tags=["User Preferences"])


# =============================================================================
# DEFAULT PREFERENCES
# =============================================================================

DEFAULT_PREFERENCES = {
    "theme": "system",  # light, dark, system
    "language": "en",
    "timezone": "UTC",
    "date_format": "YYYY-MM-DD",
    "time_format": "24h",
    "notifications": {
        "email": True,
        "push": True,
        "in_app": True,
        "digest": "daily",
    },
    "privacy": {
        "show_email": False,
        "show_activity": True,
        "allow_mentions": True,
    },
    "accessibility": {
        "reduced_motion": False,
        "high_contrast": False,
        "font_size": "medium",
    },
    "dashboard": {
        "default_view": "overview",
        "widgets": ["activity", "stats", "recent"],
    },
}


# =============================================================================
# PREFERENCE STORAGE
# =============================================================================


def get_user_prefs_key(user_id: str) -> str:
    """Retrieve user prefs key.

    Args:
        user_id: The user_id.
    """

    return f"user_prefs:{user_id}"


def get_user_preferences(user_id: str) -> dict[str, Any]:
    """Get user preferences with defaults."""
    key = get_user_prefs_key(user_id)
    prefs = cache.get(key)
    if prefs is None:
        prefs = DEFAULT_PREFERENCES.copy()
        cache.set(key, prefs, timeout=86400)
    return prefs


def set_user_preferences(user_id: str, prefs: dict[str, Any]):
    """Set user preferences."""
    key = get_user_prefs_key(user_id)
    cache.set(key, prefs, timeout=86400)


# =============================================================================
# SCHEMAS
# =============================================================================


class UserProfileOut(Schema):
    """User profile output."""

    id: str
    email: str
    display_name: str | None
    avatar_url: str | None
    bio: str | None
    role: str
    is_active: bool
    created_at: str
    last_login_at: str | None


class UserProfileUpdate(Schema):
    """Update user profile."""

    display_name: str | None = None
    avatar_url: str | None = None
    bio: str | None = None


class PreferencesOut(Schema):
    """User preferences output."""

    theme: str
    language: str
    timezone: str
    date_format: str
    time_format: str
    notifications: dict[str, Any]
    privacy: dict[str, Any]
    accessibility: dict[str, Any]
    dashboard: dict[str, Any]


class PreferencesUpdate(Schema):
    """Update preferences."""

    theme: str | None = None
    language: str | None = None
    timezone: str | None = None
    date_format: str | None = None
    time_format: str | None = None
    notifications: dict[str, Any] | None = None
    privacy: dict[str, Any] | None = None
    accessibility: dict[str, Any] | None = None
    dashboard: dict[str, Any] | None = None


class NotificationPrefs(Schema):
    """Notification preferences."""

    email: bool = True
    push: bool = True
    in_app: bool = True
    digest: str = "daily"


# =============================================================================
# PROFILE ENDPOINTS
# =============================================================================


@router.get("/me", response=UserProfileOut)
@require_auth(roles=["super-admin", "tenant-admin", "tenant-user"], any_role=True)
def get_my_profile(request: AuthenticatedRequest):
    """
    Get current user's profile.

    🎨 UX: Self-service profile
    """
    user = get_object_or_404(TenantUser, id=request.user_id)

    return UserProfileOut(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        avatar_url=getattr(user, "avatar_url", None),
        bio=getattr(user, "bio", None),
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else None,
        last_login_at=(
            user.last_login_at.isoformat()
            if hasattr(user, "last_login_at") and user.last_login_at
            else None
        ),
    )


@router.patch("/me", response=UserProfileOut)
@require_auth(roles=["super-admin", "tenant-admin", "tenant-user"], any_role=True)
def update_my_profile(
    request: AuthenticatedRequest,
    data: UserProfileUpdate,
):
    """
    Update current user's profile.

    🔒 Security: User can update own profile
    """
    user = get_object_or_404(TenantUser, id=request.user_id)

    if data.display_name is not None:
        user.display_name = data.display_name
    if data.avatar_url is not None:
        if hasattr(user, "avatar_url"):
            user.avatar_url = data.avatar_url
    if data.bio is not None:
        if hasattr(user, "bio"):
            user.bio = data.bio

    user.save()

    # Audit log
    AuditLog.log(
        action="profile.updated",
        resource_type="UserProfile",
        resource_id=str(user.id),
        actor_id=str(request.user_id),
        actor_type=ActorType.USER,
        tenant=user.tenant,
        details=data.dict(exclude_unset=True),
    )

    return UserProfileOut(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        avatar_url=getattr(user, "avatar_url", None),
        bio=getattr(user, "bio", None),
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else None,
        last_login_at=None,
    )


# =============================================================================
# PREFERENCES ENDPOINTS
# =============================================================================


@router.get("/me/preferences", response=PreferencesOut)
@require_auth(roles=["super-admin", "tenant-admin", "tenant-user"], any_role=True)
def get_my_preferences(request: AuthenticatedRequest):
    """
    Get current user's preferences.

    📊 Performance: Cached preferences
    """
    prefs = get_user_preferences(str(request.user_id))
    return PreferencesOut(**prefs)


@router.patch("/me/preferences", response=PreferencesOut)
@require_auth(roles=["super-admin", "tenant-admin", "tenant-user"], any_role=True)
def update_my_preferences(
    request: AuthenticatedRequest,
    data: PreferencesUpdate,
):
    """
    Update current user's preferences.

    🎨 UX: Personalization
    """
    prefs = get_user_preferences(str(request.user_id))

    # Update provided fields
    for field, value in data.dict(exclude_unset=True).items():
        if value is not None:
            if (
                isinstance(value, dict)
                and field in prefs
                and isinstance(prefs[field], dict)
            ):
                prefs[field].update(value)
            else:
                prefs[field] = value

    set_user_preferences(str(request.user_id), prefs)

    return PreferencesOut(**prefs)


@router.put("/me/preferences/notifications", response=NotificationPrefs)
@require_auth(roles=["super-admin", "tenant-admin", "tenant-user"], any_role=True)
def update_notification_preferences(
    request: AuthenticatedRequest,
    data: NotificationPrefs,
):
    """
    Update notification preferences.

    🎨 UX: Quick notification settings
    """
    prefs = get_user_preferences(str(request.user_id))
    prefs["notifications"] = data.dict()
    set_user_preferences(str(request.user_id), prefs)

    return NotificationPrefs(**prefs["notifications"])


@router.post("/me/preferences/reset")
@require_auth(roles=["super-admin", "tenant-admin", "tenant-user"], any_role=True)
def reset_my_preferences(request: AuthenticatedRequest):
    """
    Reset preferences to defaults.

    🛠️ DevOps: Default configuration
    """
    set_user_preferences(str(request.user_id), DEFAULT_PREFERENCES.copy())

    return {"success": True, "message": "Preferences reset to defaults"}


# =============================================================================
# ADMIN PROFILE MANAGEMENT
# =============================================================================


@router.get("/{tenant_id}/users/{user_id}", response=UserProfileOut)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.USERS_READ.value)
def get_user_profile(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    user_id: UUID,
):
    """
    Get any user's profile (admin only).

    🔒 Security: Admin access
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    user = get_object_or_404(TenantUser, id=user_id, tenant_id=tenant_id)

    return UserProfileOut(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        avatar_url=getattr(user, "avatar_url", None),
        bio=getattr(user, "bio", None),
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else None,
        last_login_at=None,
    )


@router.patch("/{tenant_id}/users/{user_id}", response=UserProfileOut)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.USERS_UPDATE.value)
def update_user_profile(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    user_id: UUID,
    data: UserProfileUpdate,
):
    """
    Update any user's profile (admin only).

    🔒 Security: Admin management
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    user = get_object_or_404(TenantUser, id=user_id, tenant_id=tenant_id)

    if data.display_name is not None:
        user.display_name = data.display_name

    user.save()

    # Audit log
    AuditLog.log(
        action="user.profile_updated",
        resource_type="UserProfile",
        resource_id=str(user.id),
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        tenant=user.tenant,
        details=data.dict(exclude_unset=True),
    )

    return UserProfileOut(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        avatar_url=getattr(user, "avatar_url", None),
        bio=getattr(user, "bio", None),
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at.isoformat() if user.created_at else None,
        last_login_at=None,
    )


@router.get("/{tenant_id}/users/{user_id}/preferences", response=PreferencesOut)
@require_auth(roles=["super-admin", "tenant-admin"], any_role=True)
@require_permission(Permission.USERS_READ.value)
def get_user_preferences_admin(
    request: AuthenticatedRequest,
    tenant_id: UUID,
    user_id: UUID,
):
    """
    Get any user's preferences (admin only).

    🔒 Security: Admin view
    """
    # Tenant isolation
    if not request.is_super_admin:
        if str(request.tenant_id) != str(tenant_id):
            from ninja.errors import HttpError

            raise HttpError(403, "Access denied")

    # Verify user exists
    get_object_or_404(TenantUser, id=user_id, tenant_id=tenant_id)

    prefs = get_user_preferences(str(user_id))
    return PreferencesOut(**prefs)


# =============================================================================
# AVAILABLE OPTIONS
# =============================================================================


@router.get("/options/themes")
def list_available_themes():
    """List available themes."""
    return {
        "themes": [
            {"id": "light", "name": "Light", "description": "Light mode theme"},
            {"id": "dark", "name": "Dark", "description": "Dark mode theme"},
            {
                "id": "system",
                "name": "System",
                "description": "Follow system preference",
            },
        ]
    }


@router.get("/options/languages")
def list_available_languages():
    """List available languages."""
    return {
        "languages": [
            {"code": "en", "name": "English"},
            {"code": "es", "name": "Spanish"},
            {"code": "fr", "name": "French"},
            {"code": "de", "name": "German"},
            {"code": "pt", "name": "Portuguese"},
            {"code": "ja", "name": "Japanese"},
            {"code": "zh", "name": "Chinese"},
        ]
    }


@router.get("/options/timezones")
def list_available_timezones():
    """List common timezones."""
    return {
        "timezones": [
            "UTC",
            "America/New_York",
            "America/Los_Angeles",
            "America/Chicago",
            "Europe/London",
            "Europe/Paris",
            "Europe/Berlin",
            "Asia/Tokyo",
            "Asia/Shanghai",
            "Asia/Singapore",
            "Australia/Sydney",
        ]
    }
