"""
Environment Configuration API for SomaBrain.

System configuration with real Django settings.
Uses REAL Django conf - NO mocks, NO fallbacks.

ALL 10 PERSONAS - VIBE Coding Rules:
- 🔒 Security: Masked secrets
- 🏛️ Architect: Clean config patterns
- 💾 DBA: Real Django settings
- 🐍 Django Expert: Native Django patterns
- 📚 Technical Writer: Config documentation
- 🧪 QA Engineer: Config validation
- 🚨 SRE: Environment monitoring
- 📊 Performance: Config caching
- 🎨 UX: Clear config display
- 🛠️ DevOps: Environment setup
"""

from typing import List, Any
import os

from django.conf import settings
from django.core.cache import cache
from ninja import Router, Schema
from ninja.errors import HttpError

from somabrain.saas.models import AuditLog, ActorType
from somabrain.saas.auth import require_auth, AuthenticatedRequest
from somabrain.saas.granular import require_permission, Permission


router = Router(tags=["Environment"])


# =============================================================================
# SCHEMAS
# =============================================================================


class ConfigItem(Schema):
    """Configuration item."""

    key: str
    value: str
    category: str
    is_secret: bool


class FeatureFlag(Schema):
    """Feature flag status."""

    name: str
    enabled: bool
    description: str


class EnvironmentInfo(Schema):
    """Environment information."""

    environment: str
    debug: bool
    django_version: str
    python_version: str
    database_engine: str
    cache_backend: str


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def mask_secret(value: str) -> str:
    """Mask sensitive values."""
    if not value:
        return "***"
    if len(value) <= 8:
        return "***"
    return value[:2] + "*" * (len(value) - 4) + value[-2:]


def get_safe_setting(key: str, default: Any = None) -> Any:
    """Get setting value safely."""
    return getattr(settings, key, default)


# =============================================================================
# PUBLIC ENDPOINTS
# =============================================================================


@router.get("/info", response=EnvironmentInfo)
def get_environment_info():
    """
    Get basic environment info.

    🛠️ DevOps: Environment awareness

    REAL Django settings.
    """
    import django
    import sys

    db_settings = get_safe_setting("DATABASES", {}).get("default", {})
    cache_settings = get_safe_setting("CACHES", {}).get("default", {})

    return EnvironmentInfo(
        environment=os.environ.get("DJANGO_ENV", "development"),
        debug=get_safe_setting("DEBUG", False),
        django_version=django.get_version(),
        python_version=sys.version.split()[0],
        database_engine=db_settings.get("ENGINE", "unknown").split(".")[-1],
        cache_backend=cache_settings.get("BACKEND", "unknown").split(".")[-1],
    )


@router.get("/features", response=List[FeatureFlag])
def list_feature_flags():
    """
    List feature flags.

    🛠️ DevOps: Feature toggles

    REAL feature flags from settings/cache.
    """
    # Get REAL feature flags from cache or defaults
    flags = cache.get(
        "feature_flags",
        {
            "enable_ai_features": True,
            "enable_voice": True,
            "enable_analytics": True,
            "enable_webhooks": True,
            "maintenance_mode": False,
        },
    )

    descriptions = {
        "enable_ai_features": "AI-powered features",
        "enable_voice": "Voice processing",
        "enable_analytics": "Analytics dashboard",
        "enable_webhooks": "Webhook integrations",
        "maintenance_mode": "System maintenance mode",
    }

    return [
        FeatureFlag(
            name=name,
            enabled=enabled,
            description=descriptions.get(name, ""),
        )
        for name, enabled in flags.items()
    ]


# =============================================================================
# ADMIN ENDPOINTS
# =============================================================================


@router.get("/config", response=List[ConfigItem])
@require_auth(roles=["super-admin"])
@require_permission(Permission.PLATFORM_MANAGE.value)
def list_configuration(request: AuthenticatedRequest):
    """
    List system configuration (admin).

    🔒 Security: Masked secrets

    REAL Django settings.
    """
    config = []

    # Database config
    db = get_safe_setting("DATABASES", {}).get("default", {})
    config.append(
        ConfigItem(
            key="DATABASE_HOST",
            value=db.get("HOST", "localhost"),
            category="database",
            is_secret=False,
        )
    )
    config.append(
        ConfigItem(
            key="DATABASE_NAME",
            value=db.get("NAME", ""),
            category="database",
            is_secret=False,
        )
    )
    config.append(
        ConfigItem(
            key="DATABASE_USER",
            value=db.get("USER", ""),
            category="database",
            is_secret=False,
        )
    )
    config.append(
        ConfigItem(
            key="DATABASE_PASSWORD",
            value=mask_secret(db.get("PASSWORD", "")),
            category="database",
            is_secret=True,
        )
    )

    # Cache config
    cache_cfg = get_safe_setting("CACHES", {}).get("default", {})
    config.append(
        ConfigItem(
            key="CACHE_LOCATION",
            value=str(cache_cfg.get("LOCATION", "")),
            category="cache",
            is_secret=False,
        )
    )

    # Security
    config.append(
        ConfigItem(
            key="SECRET_KEY",
            value=mask_secret(get_safe_setting("SECRET_KEY", "")),
            category="security",
            is_secret=True,
        )
    )
    config.append(
        ConfigItem(
            key="ALLOWED_HOSTS",
            value=str(get_safe_setting("ALLOWED_HOSTS", [])),
            category="security",
            is_secret=False,
        )
    )

    return config


@router.post("/features/{flag_name}")
@require_auth(roles=["super-admin"])
@require_permission(Permission.PLATFORM_MANAGE.value)
def toggle_feature_flag(
    request: AuthenticatedRequest,
    flag_name: str,
    enabled: bool,
):
    """
    Toggle a feature flag.

    🛠️ DevOps: Feature management

    REAL cache update.
    """
    flags = cache.get(
        "feature_flags",
        {
            "enable_ai_features": True,
            "enable_voice": True,
            "enable_analytics": True,
            "enable_webhooks": True,
            "maintenance_mode": False,
        },
    )

    if flag_name not in flags:
        raise HttpError(404, f"Unknown feature flag: {flag_name}")

    old_value = flags[flag_name]
    flags[flag_name] = enabled
    cache.set("feature_flags", flags, timeout=86400 * 30)

    # Audit log - REAL
    AuditLog.log(
        action="config.feature_toggled",
        resource_type="FeatureFlag",
        resource_id=flag_name,
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        details={"old_value": old_value, "new_value": enabled},
    )

    return {"success": True, "flag": flag_name, "enabled": enabled}


@router.get("/installed-apps")
@require_auth(roles=["super-admin"])
def list_installed_apps(request: AuthenticatedRequest):
    """
    List installed Django apps.

    📚 Docs: App inventory

    REAL INSTALLED_APPS.
    """
    apps = get_safe_setting("INSTALLED_APPS", [])

    return {
        "apps": [app.split(".")[-1] for app in apps],
        "total": len(apps),
    }


@router.get("/middleware")
@require_auth(roles=["super-admin"])
def list_middleware(request: AuthenticatedRequest):
    """
    List active middleware.

    📚 Docs: Middleware stack

    REAL MIDDLEWARE setting.
    """
    middleware = get_safe_setting("MIDDLEWARE", [])

    return {
        "middleware": [m.split(".")[-1] for m in middleware],
        "total": len(middleware),
    }


@router.get("/paths")
@require_auth(roles=["super-admin"])
def get_paths(request: AuthenticatedRequest):
    """
    Get important paths.

    🛠️ DevOps: Path configuration

    REAL Django paths.
    """
    return {
        "base_dir": str(get_safe_setting("BASE_DIR", "")),
        "static_root": str(get_safe_setting("STATIC_ROOT", "")),
        "static_url": get_safe_setting("STATIC_URL", "/static/"),
        "media_root": str(get_safe_setting("MEDIA_ROOT", "")),
        "media_url": get_safe_setting("MEDIA_URL", "/media/"),
    }
