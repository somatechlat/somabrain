"""SomaBrain API v1 - Django Ninja

Central API instance for all SomaBrain endpoints.
100% Django Ninja - VIBE Coding Rules compliant.

All routers are registered here for clean architecture.
"""

from ninja import NinjaAPI

api = NinjaAPI(
    title="SomaBrain API",
    version="1.0.0",
    description="Cognitive Architecture API - Advanced AI System",
    docs_url="/docs",
)


def _safe_add_router(api_instance, prefix, router, **kwargs):
    """Safely add router, clearing attached flag if needed for autoreload.
    
    Django Ninja routers remember when they're attached, causing ConfigError
    on Django autoreload. This helper clears the internal state.
    Router.build_routers() checks 'self.api is not None' at ninja/router.py:454
    """
    # Clear the router's attached API reference to allow re-attachment
    # The attribute checked in build_routers() is 'api' not '_api'
    if hasattr(router, 'api') and router.api is not None:
        router.api = None
    api_instance.add_router(prefix, router, **kwargs)


# =============================================================================
# ROUTER REGISTRATION - ALL ROUTERS CONSOLIDATED HERE
# =============================================================================

# SaaS Admin Router - Tenant management, API keys, subscriptions
from somabrain.api.endpoints.saas_admin import router as saas_admin_router
_safe_add_router(api, "/saas/", saas_admin_router, tags=["SaaS Admin"])

# Auth Router - Login, OAuth callback, session management
from somabrain.api.endpoints.auth import router as auth_router
_safe_add_router(api, "/auth/", auth_router, tags=["Authentication"])

# Health Router
from somabrain.api.endpoints.health import router as health_router
_safe_add_router(api, "/health/", health_router, tags=["Health"])

# Admin Router (system admin, not SaaS)
from somabrain.api.endpoints.admin import router as admin_router
_safe_add_router(api, "/admin/", admin_router, tags=["Admin"])

# Admin Journal
from somabrain.api.endpoints.admin_journal import router as admin_journal_router
_safe_add_router(api, "/admin/journal/", admin_journal_router, tags=["Admin"])

# Cognitive Router
from somabrain.api.endpoints.cognitive import router as cognitive_router
_safe_add_router(api, "/cognitive/", cognitive_router, tags=["Cognitive"])

# Sleep Router
from somabrain.api.endpoints.sleep import router as sleep_router
_safe_add_router(api, "/sleep/", sleep_router, tags=["Sleep"])

# Neuromod Router
from somabrain.api.endpoints.neuromod import router as neuromod_router
_safe_add_router(api, "/neuromod/", neuromod_router, tags=["Neuromod"])

# Proxy Router
from somabrain.api.endpoints.proxy import router as proxy_router
_safe_add_router(api, "/proxy/", proxy_router, tags=["Proxy"])

# Config Router
from somabrain.api.endpoints.config import router as config_router
_safe_add_router(api, "/config/", config_router, tags=["Config"])

# Memory Routers
from somabrain.api.endpoints.memory import router as memory_router
_safe_add_router(api, "/memory/", memory_router, tags=["Memory"])

from somabrain.api.endpoints.memory_admin import router as memory_admin_router
_safe_add_router(api, "/memory/admin/", memory_admin_router, tags=["Memory Admin"])

from somabrain.api.endpoints.memory_remember import router as memory_remember_router
_safe_add_router(api, "/memory/remember/", memory_remember_router, tags=["Memory"])

# Context Router
from somabrain.api.endpoints.context import router as context_router
_safe_add_router(api, "/context/", context_router, tags=["Context"])

# Features Router
from somabrain.api.endpoints.features import router as features_router
_safe_add_router(api, "/features/", features_router, tags=["Features"])

# Persona Router
from somabrain.api.endpoints.persona import router as persona_router
_safe_add_router(api, "/persona/", persona_router, tags=["Persona"])

# Constitution Router
from somabrain.api.endpoints.constitution import router as constitution_router
_safe_add_router(api, "/constitution/", constitution_router, tags=["Constitution"])

# Thread Router (root level)
from somabrain.api.endpoints.thread import router as thread_router
_safe_add_router(api, "/threads/", thread_router, tags=["Thread"])

# Oak Router
from somabrain.api.endpoints.oak import router as oak_router
_safe_add_router(api, "/oak/", oak_router, tags=["Oak"])

# OPA Router
from somabrain.api.endpoints.opa import router as opa_router
_safe_add_router(api, "/opa/", opa_router, tags=["OPA"])

# Calibration Router
from somabrain.api.endpoints.calibration import router as calibration_router
_safe_add_router(api, "/calibration/", calibration_router, tags=["Calibration"])

# Identity Providers Router (OAuth admin)
from somabrain.api.endpoints.identity_providers import router as identity_providers_router
_safe_add_router(api, "/identity-providers/", identity_providers_router, tags=["Identity Providers"])

# Roles & Permissions Router
from somabrain.api.endpoints.roles import router as roles_router
_safe_add_router(api, "/roles/", roles_router, tags=["Roles"])

# Users Router
from somabrain.api.endpoints.users import router as users_router
_safe_add_router(api, "/users/", users_router, tags=["Users"])

# Tenant Auth Settings Router
from somabrain.api.endpoints.tenant_auth import router as tenant_auth_router
_safe_add_router(api, "/tenant-auth/", tenant_auth_router, tags=["Tenant Auth"])

# Billing Router
from somabrain.api.endpoints.billing import router as billing_router
_safe_add_router(api, "/billing/", billing_router, tags=["Billing"])

# Admin Dashboard Router
from somabrain.api.endpoints.dashboard import router as dashboard_router
_safe_add_router(api, "/admin/dashboard/", dashboard_router, tags=["Admin Dashboard"])

# Tenant Analytics Router
from somabrain.api.endpoints.analytics import router as analytics_router
_safe_add_router(api, "/analytics/", analytics_router, tags=["Tenant Analytics"])

# Webhooks Router
from somabrain.api.endpoints.webhooks import router as webhooks_router
_safe_add_router(api, "/webhooks/", webhooks_router, tags=["Webhooks"])

# Notifications Router
from somabrain.api.endpoints.notifications import router as notifications_router
_safe_add_router(api, "/notifications/", notifications_router, tags=["Notifications"])

# System Health Router (Comprehensive)
from somabrain.api.endpoints.system_health import router as system_health_router
_safe_add_router(api, "/health/", system_health_router, tags=["Health"])

# Audit Logs Router
from somabrain.api.endpoints.audit_logs import router as audit_logs_router
_safe_add_router(api, "/audit/", audit_logs_router, tags=["Audit Logs"])

# Feature Flags Router
from somabrain.api.endpoints.feature_flags import router as feature_flags_router
_safe_add_router(api, "/features/", feature_flags_router, tags=["Feature Flags"])

# Onboarding Wizard Router
from somabrain.api.endpoints.onboarding import router as onboarding_router
_safe_add_router(api, "/onboarding/", onboarding_router, tags=["Onboarding"])

# Reports Router
from somabrain.api.endpoints.reports import router as reports_router
_safe_add_router(api, "/reports/", reports_router, tags=["Reports"])

# Settings Router
from somabrain.api.endpoints.settings import router as settings_router
_safe_add_router(api, "/settings/", settings_router, tags=["Settings"])

# Invitations Router
from somabrain.api.endpoints.invitations import router as invitations_router
_safe_add_router(api, "/invitations/", invitations_router, tags=["Invitations"])

# Import/Export Router
from somabrain.api.endpoints.import_export import router as import_export_router
_safe_add_router(api, "/import-export/", import_export_router, tags=["Import/Export"])

# Search Router
from somabrain.api.endpoints.search import router as search_router
_safe_add_router(api, "/search/", search_router, tags=["Search"])

# System Config Router
from somabrain.api.endpoints.system_config import router as system_config_router
_safe_add_router(api, "/system/", system_config_router, tags=["System"])

# Activity Router
from somabrain.api.endpoints.activity import router as activity_router
_safe_add_router(api, "/activity/", activity_router, tags=["Activity"])

# Backup Router
from somabrain.api.endpoints.backup import router as backup_router
_safe_add_router(api, "/backup/", backup_router, tags=["Backup"])

# Versioning Router
from somabrain.api.endpoints.versioning import router as versioning_router
_safe_add_router(api, "/versioning/", versioning_router, tags=["API Versioning"])

# API Metrics Router
from somabrain.api.endpoints.api_metrics import router as api_metrics_router
_safe_add_router(api, "/metrics/", api_metrics_router, tags=["Metrics"])

# API Keys Enhanced Router
from somabrain.api.endpoints.api_keys_enhanced import router as api_keys_enhanced_router
_safe_add_router(api, "/keys/", api_keys_enhanced_router, tags=["API Keys (Enhanced)"])

# User Preferences Router
from somabrain.api.endpoints.user_preferences import router as user_preferences_router
_safe_add_router(api, "/profile/", user_preferences_router, tags=["User Preferences"])

# Teams Router
from somabrain.api.endpoints.teams import router as teams_router
_safe_add_router(api, "/teams/", teams_router, tags=["Teams"])

# Branding Router
from somabrain.api.endpoints.branding import router as branding_router
_safe_add_router(api, "/branding/", branding_router, tags=["Branding"])

# SSO Router
from somabrain.api.endpoints.sso import router as sso_router
_safe_add_router(api, "/sso/", sso_router, tags=["SSO"])

# Retention Router
from somabrain.api.endpoints.retention import router as retention_router
_safe_add_router(api, "/retention/", retention_router, tags=["Data Retention"])

# Request Logs Router
from somabrain.api.endpoints.request_logs import router as request_logs_router
_safe_add_router(api, "/request-logs/", request_logs_router, tags=["Request Logs"])

# Geo Access Router
from somabrain.api.endpoints.geo_access import router as geo_access_router
_safe_add_router(api, "/geo/", geo_access_router, tags=["Geo Access"])

# Playground Router
from somabrain.api.endpoints.playground import router as playground_router
_safe_add_router(api, "/playground/", playground_router, tags=["API Playground"])

# Changelog Router
from somabrain.api.endpoints.changelog import router as changelog_router
_safe_add_router(api, "/changelog/", changelog_router, tags=["Changelog"])

# License Router
from somabrain.api.endpoints.license import router as license_router
_safe_add_router(api, "/license/", license_router, tags=["Licensing"])

# Sessions Router
from somabrain.api.endpoints.sessions import router as sessions_router
_safe_add_router(api, "/sessions/", sessions_router, tags=["Sessions"])

# Rate Limits Router
from somabrain.api.endpoints.rate_limits import router as rate_limits_router
_safe_add_router(api, "/rate-limits/", rate_limits_router, tags=["Rate Limits"])

# Quotas Router
from somabrain.api.endpoints.quotas import router as quotas_router
_safe_add_router(api, "/quotas/", quotas_router, tags=["Quotas"])

# User Notifications Router
from somabrain.api.endpoints.user_notifications import router as user_notifications_router
_safe_add_router(api, "/notifications/", user_notifications_router, tags=["Notifications"])

# Webhooks Dashboard Router
from somabrain.api.endpoints.webhooks_dashboard import router as webhooks_dashboard_router
_safe_add_router(api, "/webhooks-dashboard/", webhooks_dashboard_router, tags=["Webhooks Dashboard"])

# Service Health Router
from somabrain.api.endpoints.service_health import router as service_health_router
_safe_add_router(api, "/service-health/", service_health_router, tags=["Service Health"])

# Admin Override Router
from somabrain.api.endpoints.admin_override import router as admin_override_router
_safe_add_router(api, "/admin-override/", admin_override_router, tags=["Admin Override"])

# Environment Router
from somabrain.api.endpoints.environment import router as environment_router
_safe_add_router(api, "/environment/", environment_router, tags=["Environment"])

# System Metrics Router
from somabrain.api.endpoints.system_metrics import router as system_metrics_router
_safe_add_router(api, "/metrics/", system_metrics_router, tags=["System Metrics"])

