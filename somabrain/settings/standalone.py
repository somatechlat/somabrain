
"""
Standalone Settings Profile.
STRICTLY ISOLATED from AAAS/Multi-tenancy logic.
Usage: DJANGO_SETTINGS_MODULE=somabrain.settings.standalone
"""
from .django_core import *
from .infra import *
from .cognitive import *
from .neuro import *

# =============================================================================
# STANDALONE ISOLATION - STRIP AAAS
# =============================================================================

# Remove AAAS Application
INSTALLED_APPS = [
    app for app in INSTALLED_APPS
    if "aaas" not in app
    and app != "somabrain.aaas"
]

# Remove AAAS Middleware (Billing, Rate Limiting, etc)
MIDDLEWARE = [
    m for m in MIDDLEWARE
    if "somabrain.aaas" not in m
    and "UsageTrackingMiddleware" not in m
]

# Disable Tenant/AAAS Features
SOMABRAIN_REQUIRE_EXTERNAL_BACKENDS = False  # Allow running with minimal deps
SOMABRAIN_DEFAULT_TENANT = "standalone"
SOMABRAIN_TENANT_ID = "standalone"

print(f"Loaded STANDALONE settings. Apps: {len(INSTALLED_APPS)}")
