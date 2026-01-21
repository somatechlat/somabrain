"""Config API - Django Ninja Version

Migrated from FastAPI to Django Ninja.
Configuration management endpoints.
"""

from __future__ import annotations

import logging

from django.conf import settings
from django.http import HttpRequest
from ninja import Router

from somabrain.api.auth import bearer_auth
from somabrain.auth import require_auth
from somabrain.schemas import ConfigResponse
from somabrain.tenant import get_tenant

logger = logging.getLogger("somabrain.api.endpoints.config")

router = Router(tags=["config"])


@router.get("/", response=ConfigResponse, auth=bearer_auth)
def get_config(request: HttpRequest):
    """Get current configuration for tenant."""
    ctx = get_tenant(request, getattr(settings, "NAMESPACE", "default"))
    require_auth(request, settings)

    # Return sanitized configuration (no secrets)
    config_data = {
        "tenant_id": ctx.tenant_id,
        "namespace": ctx.namespace,
        "features": {
            "enable_sleep": getattr(settings, "SOMABRAIN_ENABLE_SLEEP", True),
            "consolidation_enabled": getattr(
                settings, "SOMABRAIN_CONSOLIDATION_ENABLED", True
            ),
            "use_planner": getattr(settings, "USE_PLANNER", False),
            "use_microcircuits": getattr(settings, "USE_MICROCIRCUITS", False),
        },
        "limits": {
            "plan_max_steps": getattr(settings, "PLAN_MAX_STEPS", 5),
            "hrr_dim": getattr(settings, "HRR_DIM", 512),
        },
    }

    return ConfigResponse(**config_data)
