"""Neuromod Router - Django Ninja Version

Migrated from FastAPI to Django Ninja.
Neuromodulator management endpoints.
"""

from __future__ import annotations

import logging
from ninja import Router
from django.http import HttpRequest

from django.conf import settings
from somabrain.schemas import NeuromodAdjustRequest

from somabrain.api.auth import bearer_auth
from somabrain.auth import require_auth
from somabrain.tenant import get_tenant

logger = logging.getLogger("somabrain.api.endpoints.neuromod")

router = Router(tags=["neuromod"])


@router.get("/state", auth=bearer_auth)
def get_neuromod_state(request: HttpRequest):
    """Get neuromodulator state for tenant."""
    ctx = get_tenant(request, getattr(settings, "NAMESPACE", "default"))
    require_auth(request, settings)
    
    # Get neuromodulator values from app singletons
    try:
        from somabrain import app as app_module
        neuromod_manager = getattr(app_module, "per_tenant_neuromodulators", None)
        
        if neuromod_manager and hasattr(neuromod_manager, "get"):
            values = neuromod_manager.get(ctx.tenant_id)
        else:
            # Default values
            values = {
                "dopamine": 0.5,
                "serotonin": 0.5,
                "noradrenaline": 0.5,
                "acetylcholine": 0.5,
            }
    except Exception as exc:
        logger.warning(f"Failed to get neuromod state: {exc}")
        values = {
            "dopamine": 0.5,
            "serotonin": 0.5,
            "noradrenaline": 0.5,
            "acetylcholine": 0.5,
        }
    
    return {
        "tenant_id": ctx.tenant_id,
        "dopamine": values.get("dopamine", 0.5),
        "serotonin": values.get("serotonin", 0.5),
        "noradrenaline": values.get("noradrenaline", 0.5),
        "acetylcholine": values.get("acetylcholine", 0.5),
    }


@router.post("/adjust", auth=bearer_auth)
def adjust_neuromod(request: HttpRequest, body: NeuromodAdjustRequest):
    """Adjust neuromodulator values for tenant."""
    ctx = get_tenant(request, getattr(settings, "NAMESPACE", "default"))
    require_auth(request, settings)
    
    try:
        from somabrain import app as app_module
        neuromod_manager = getattr(app_module, "per_tenant_neuromodulators", None)
        
        if neuromod_manager and hasattr(neuromod_manager, "adjust"):
            # Apply adjustments
            adjustments = {}
            if hasattr(body, "dopamine"):
                adjustments["dopamine"] = body.dopamine
            if hasattr(body, "serotonin"):
                adjustments["serotonin"] = body.serotonin
            if hasattr(body, "noradrenaline"):
                adjustments["noradrenaline"] = body.noradrenaline
            if hasattr(body, "acetylcholine"):
                adjustments["acetylcholine"] = body.acetylcholine
                
            neuromod_manager.adjust(ctx.tenant_id, **adjustments)
            values = neuromod_manager.get(ctx.tenant_id)
        else:
            values = {
                "dopamine": getattr(body, "dopamine", 0.5),
                "serotonin": getattr(body, "serotonin", 0.5),
                "noradrenaline": getattr(body, "noradrenaline", 0.5),
                "acetylcholine": getattr(body, "acetylcholine", 0.5),
            }
            
        logger.info(f"Neuromod adjusted for {ctx.tenant_id}")
        
    except Exception as exc:
        logger.error(f"Failed to adjust neuromod: {exc}")
        values = {
            "dopamine": 0.5,
            "serotonin": 0.5,
            "noradrenaline": 0.5,
            "acetylcholine": 0.5,
        }
    
    return {
        "tenant_id": ctx.tenant_id,
        "dopamine": values.get("dopamine", 0.5),
        "serotonin": values.get("serotonin", 0.5),
        "noradrenaline": values.get("noradrenaline", 0.5),
        "acetylcholine": values.get("acetylcholine", 0.5),
    }