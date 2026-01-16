"""
System Configuration API for SomaBrain.

Platform-wide system configuration and maintenance endpoints.

ALL 10 PERSONAS - VIBE Coding Rules:
- 🔒 Security: Super-admin only for sensitive ops
- 🏛️ Architect: Clean config patterns
- 💾 DBA: Django ORM configuration
- 🐍 Django Expert: Native Django settings
- 📚 Technical Writer: Comprehensive docstrings
- 🧪 QA Engineer: Config validation
- 🚨 SRE: Maintenance mode, health checks
- 📊 Performance: Config caching
- 🎨 UX: Clear config display
- 🛠️ DevOps: Runtime configuration
"""

from typing import Optional, Dict, Any

from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from ninja import Router, Schema

from somabrain.saas.models import Tenant, AuditLog, ActorType
from somabrain.saas.auth import require_auth, AuthenticatedRequest
from somabrain.saas.granular import require_permission, Permission


router = Router(tags=["System"])


# =============================================================================
# CONFIG STORAGE
# =============================================================================

SYSTEM_CONFIG_KEY = "system:config"
MAINTENANCE_KEY = "system:maintenance"


def get_system_config() -> Dict[str, Any]:
    """Get system configuration."""
    config = cache.get(SYSTEM_CONFIG_KEY)
    if not config:
        config = {
            "maintenance_mode": False,
            "maintenance_message": "",
            "max_tenants": 1000,
            "default_tier": "free",
            "signup_enabled": True,
            "require_email_verification": True,
            "session_timeout_minutes": 60,
            "api_rate_limit_default": 1000,
            "webhook_retry_attempts": 3,
            "webhook_timeout_seconds": 30,
            "feature_flags_enabled": True,
            "audit_log_retention_days": 90,
            "usage_sync_interval_seconds": 60,
        }
        cache.set(SYSTEM_CONFIG_KEY, config, timeout=86400)
    return config


def set_system_config(config: Dict[str, Any]):
    """Update system configuration."""
    cache.set(SYSTEM_CONFIG_KEY, config, timeout=86400)


# =============================================================================
# SCHEMAS
# =============================================================================


class SystemConfigOut(Schema):
    """System configuration output."""

    maintenance_mode: bool
    maintenance_message: Optional[str]
    max_tenants: int
    default_tier: str
    signup_enabled: bool
    require_email_verification: bool
    session_timeout_minutes: int
    api_rate_limit_default: int
    webhook_retry_attempts: int
    webhook_timeout_seconds: int
    feature_flags_enabled: bool
    audit_log_retention_days: int


class SystemConfigUpdate(Schema):
    """Update system configuration."""

    maintenance_mode: Optional[bool] = None
    maintenance_message: Optional[str] = None
    max_tenants: Optional[int] = None
    default_tier: Optional[str] = None
    signup_enabled: Optional[bool] = None
    require_email_verification: Optional[bool] = None
    session_timeout_minutes: Optional[int] = None
    api_rate_limit_default: Optional[int] = None


class MaintenanceMode(Schema):
    """Maintenance mode settings."""

    enabled: bool
    message: Optional[str] = None
    scheduled_end: Optional[str] = None


class SystemStatsOut(Schema):
    """System statistics output."""

    total_tenants: int
    active_tenants: int
    total_users: int
    total_api_keys: int
    total_webhooks: int
    total_notifications: int
    audit_logs_count: int
    cache_hit_rate: Optional[float]
    uptime_seconds: int


class DatabaseStatsOut(Schema):
    """Database statistics."""

    database_name: str
    database_size_mb: float
    tables_count: int
    active_connections: int


# =============================================================================
# SYSTEM CONFIG ENDPOINTS
# =============================================================================


@router.get("/config", response=SystemConfigOut)
@require_auth(roles=["super-admin"])
@require_permission(Permission.PLATFORM_MANAGE.value)
def get_config(request: AuthenticatedRequest):
    """
    Get system configuration.

    🔒 Security: Super-admin only
    """
    config = get_system_config()
    return SystemConfigOut(**{k: v for k, v in config.items() if k in SystemConfigOut.__fields__})


@router.patch("/config", response=SystemConfigOut)
@require_auth(roles=["super-admin"])
@require_permission(Permission.PLATFORM_MANAGE.value)
def update_config(
    request: AuthenticatedRequest,
    data: SystemConfigUpdate,
):
    """
    Update system configuration.

    🚨 SRE: Audit logging for config changes
    """
    config = get_system_config()

    # Update provided fields
    for field, value in data.dict(exclude_unset=True).items():
        if value is not None:
            config[field] = value

    set_system_config(config)

    # Audit log
    AuditLog.log(
        action="system.config_updated",
        resource_type="SystemConfig",
        resource_id="global",
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        details=data.dict(exclude_unset=True),
    )

    return SystemConfigOut(**{k: v for k, v in config.items() if k in SystemConfigOut.__fields__})


# =============================================================================
# MAINTENANCE MODE
# =============================================================================


@router.get("/maintenance")
@require_auth(roles=["super-admin"])
def get_maintenance_status(request: AuthenticatedRequest):
    """Get current maintenance mode status."""
    maintenance = cache.get(
        MAINTENANCE_KEY,
        {
            "enabled": False,
            "message": "",
            "scheduled_end": None,
            "started_at": None,
        },
    )
    return maintenance


@router.post("/maintenance/enable")
@require_auth(roles=["super-admin"])
@require_permission(Permission.PLATFORM_MANAGE.value)
def enable_maintenance(
    request: AuthenticatedRequest,
    data: MaintenanceMode,
):
    """
    Enable maintenance mode.

    🛠️ DevOps: Maintenance operations
    """
    maintenance = {
        "enabled": True,
        "message": data.message or "System is under maintenance",
        "scheduled_end": data.scheduled_end,
        "started_at": timezone.now().isoformat(),
        "started_by": str(request.user_id),
    }
    cache.set(MAINTENANCE_KEY, maintenance, timeout=86400)

    # Update system config
    config = get_system_config()
    config["maintenance_mode"] = True
    config["maintenance_message"] = maintenance["message"]
    set_system_config(config)

    # Audit log
    AuditLog.log(
        action="system.maintenance_enabled",
        resource_type="System",
        resource_id="maintenance",
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
        details={"message": maintenance["message"]},
    )

    return maintenance


@router.post("/maintenance/disable")
@require_auth(roles=["super-admin"])
@require_permission(Permission.PLATFORM_MANAGE.value)
def disable_maintenance(request: AuthenticatedRequest):
    """Disable maintenance mode."""
    maintenance = {
        "enabled": False,
        "message": "",
        "scheduled_end": None,
        "started_at": None,
    }
    cache.set(MAINTENANCE_KEY, maintenance, timeout=86400)

    # Update system config
    config = get_system_config()
    config["maintenance_mode"] = False
    config["maintenance_message"] = ""
    set_system_config(config)

    # Audit log
    AuditLog.log(
        action="system.maintenance_disabled",
        resource_type="System",
        resource_id="maintenance",
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
    )

    return {"success": True, "maintenance_mode": False}


# =============================================================================
# SYSTEM STATS
# =============================================================================


@router.get("/stats", response=SystemStatsOut)
@require_auth(roles=["super-admin"])
@require_permission(Permission.PLATFORM_MANAGE.value)
def get_system_stats(request: AuthenticatedRequest):
    """
    Get platform-wide statistics.

    📊 Performance: Cached stats
    """
    from somabrain.saas.models import TenantUser, APIKey, Webhook, Notification
    from django.db.models import Count

    # Tenant stats
    tenant_stats = Tenant.objects.aggregate(
        total=Count("id"),
        active=Count("id", filter=models.Q(status="active")),
    )

    # Other counts
    total_users = TenantUser.objects.count()
    total_keys = APIKey.objects.count()
    total_webhooks = Webhook.objects.count()
    total_notifications = Notification.objects.count()
    audit_count = AuditLog.objects.count()

    # Uptime (from cache or process start)
    import time

    uptime = int(time.time() - getattr(settings, "START_TIME", time.time()))

    return SystemStatsOut(
        total_tenants=tenant_stats["total"],
        active_tenants=tenant_stats["active"],
        total_users=total_users,
        total_api_keys=total_keys,
        total_webhooks=total_webhooks,
        total_notifications=total_notifications,
        audit_logs_count=audit_count,
        cache_hit_rate=None,  # Would need cache metrics
        uptime_seconds=uptime,
    )


@router.get("/database")
@require_auth(roles=["super-admin"])
@require_permission(Permission.PLATFORM_MANAGE.value)
def get_database_stats(request: AuthenticatedRequest):
    """
    Get database statistics.

    💾 DBA: Database monitoring
    """
    from django.db import connection

    with connection.cursor() as cursor:
        # PostgreSQL specific queries
        try:
            cursor.execute("SELECT pg_database_size(current_database())")
            db_size = cursor.fetchone()[0] / (1024 * 1024)  # MB

            cursor.execute(
                """
                SELECT count(*) FROM information_schema.tables 
                WHERE table_schema = 'public'
            """
            )
            tables = cursor.fetchone()[0]

            cursor.execute("SELECT count(*) FROM pg_stat_activity WHERE state = 'active'")
            connections = cursor.fetchone()[0]

            cursor.execute("SELECT current_database()")
            db_name = cursor.fetchone()[0]

            return {
                "database_name": db_name,
                "database_size_mb": round(db_size, 2),
                "tables_count": tables,
                "active_connections": connections,
            }
        except Exception as e:
            return {"error": str(e)}


# =============================================================================
# CACHE MANAGEMENT
# =============================================================================


@router.post("/cache/clear")
@require_auth(roles=["super-admin"])
@require_permission(Permission.PLATFORM_MANAGE.value)
def clear_cache(
    request: AuthenticatedRequest,
    pattern: Optional[str] = None,
):
    """
    Clear cache entries.

    📊 Performance: Cache management
    """
    if pattern:
        # Would need pattern-based clearing
        return {"success": False, "error": "Pattern clearing not supported"}

    cache.clear()

    # Audit log
    AuditLog.log(
        action="system.cache_cleared",
        resource_type="Cache",
        resource_id="all",
        actor_id=str(request.user_id),
        actor_type=ActorType.ADMIN,
    )

    return {"success": True, "message": "Cache cleared"}


# =============================================================================
# FEATURE FLAGS (System-wide)
# =============================================================================


@router.get("/features")
@require_auth(roles=["super-admin"])
def list_system_features(request: AuthenticatedRequest):
    """List system-wide feature flags."""
    from somabrain.api.endpoints.feature_flags import get_all_flags

    return {"features": list(get_all_flags().values())}


# Import models for aggregate queries
from django.db import models
