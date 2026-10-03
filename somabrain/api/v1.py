"""SomaBrain API v1 - Django Ninja

Central API instance for all SomaBrain endpoints.
100% Django Ninja - VIBE Coding Rules compliant.

Every router here is core brain surface and is always loaded: cognitive,
memory, health, configuration, and the cognitive mode control plane. The
commerce/product overlay that used to be registered alongside them has been
removed — SomaBrain is HTTP + containers only.
"""

import logging

from ninja import NinjaAPI

logger = logging.getLogger(__name__)

api = NinjaAPI(
    title="SomaBrain API",
    version="2.0.0",
    urls_namespace="somabrain-api",
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
    if hasattr(router, "api") and router.api is not None:
        router.api = None
    api_instance.add_router(prefix, router, **kwargs)


# =============================================================================
# CORE ROUTERS — ALWAYS LOADED
# =============================================================================

# Health Router
from somabrain.api.endpoints.health import router as health_router

_safe_add_router(api, "/health/", health_router, tags=["Health"])

# System Health Router (Comprehensive) — core infra checks
from somabrain.api.endpoints.system_health import router as system_health_router

_safe_add_router(api, "/health/", system_health_router, tags=["Health"])

# Admin Router (system admin)
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

_safe_add_router(api, "/memory/", memory_remember_router, tags=["Memory"])

# Legacy BrainBridge spellings (/remember|recall|forget) — thin aliases of the
# canonical /memory/* handlers above. Canonical contract lives at
# /api/memory/remember|recall|forget (also reachable at /memory/*).
from somabrain.api.endpoints.memory_alias import router as memory_alias_router

_safe_add_router(api, "", memory_alias_router, tags=["Memory"])

# Context Router
from somabrain.api.endpoints.context import router as context_router

_safe_add_router(api, "/context/", context_router, tags=["Context"])

# Features Router
from somabrain.api.endpoints.features import router as features_router

_safe_add_router(api, "/features/", features_router, tags=["Features"])

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

# Persona Router
from somabrain.api.endpoints.persona import router as persona_router

_safe_add_router(api, "/persona/", persona_router, tags=["Persona"])

# Constitution Router
from somabrain.api.endpoints.constitution import router as constitution_router

_safe_add_router(api, "/constitution/", constitution_router, tags=["Constitution"])


# Brain Settings Router — the cognitive mode control plane (which mode the
# brain is operating in). Core surface: it configures cognition, not a product.
from somabrain.api.endpoints.brain_settings import router as brain_settings_router

_safe_add_router(api, "/brain/", brain_settings_router, tags=["Brain Settings"])
