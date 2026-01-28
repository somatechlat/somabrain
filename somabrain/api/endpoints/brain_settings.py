"""Brain Settings Management API - Persona-Driven implementation.

Features:
- Multi-tenant tenant isolation
- AAAS Auth (JWT/API-Key)
- OPA Permission Enforcement
- Zero-Latency cognitive shifts
"""
from typing import List, Dict, Any
from ninja import Router, Schema
from django.http import HttpRequest
from somabrain.aaas.auth import api_key_or_jwt
from somabrain.aaas.granular import require_permission, Permission
from somabrain.aaas.rate_limit import rate_limit
from somabrain.brain_settings.models import BrainSetting
from somabrain.brain_settings.modes import BRAIN_MODES

router = Router(tags=["Brain Settings"])

class ModeResponse(Schema):
    mode: str
    description: str
    parameters: Dict[str, Any]

class SetModeSchema(Schema):
    mode: str

@router.get("/modes", auth=api_key_or_jwt, response=List[ModeResponse])
@rate_limit(rps=5, burst=10)
def list_brain_modes(request: HttpRequest):
    """List all available cognitive operational modes."""
    return [
        {
            "mode": k,
            "description": v["description"],
            "parameters": v["overrides"]
        } for k, v in BRAIN_MODES.items()
    ]

@router.post("/mode", auth=api_key_or_jwt)
@require_permission(Permission.SYSTEM_CONFIG)
@rate_limit(rps=1, burst=5)
def set_brain_mode(request: HttpRequest, data: SetModeSchema):
    """
    Atomic cognitive shift. Immediate cache invalidation.
    Persona: Django Architect / Security Auditor
    """
    tenant_id = request.auth.get("tenant_id", "default")
    mode = data.mode.upper()

    if mode not in BRAIN_MODES:
        from ninja.errors import HttpError
        raise HttpError(400, f"Invalid mode '{mode}'. Available: {list(BRAIN_MODES.keys())}")

    # Atomic DB update with cache invalidation
    BrainSetting.set("active_brain_mode", mode, tenant=tenant_id)

    return {
        "status": "success",
        "tenant_id": tenant_id,
        "new_mode": mode,
        "description": BRAIN_MODES[mode]["description"]
    }

@router.get("/status", auth=api_key_or_jwt)
def get_brain_status(request: HttpRequest):
    """Get current operational state and critical GMD knobs."""
    tenant_id = request.auth.get("tenant_id", "default")

    return {
        "active_mode": BrainSetting.get("active_brain_mode", tenant_id),
        "knobs": {
            "gmd_eta": BrainSetting.get("gmd_eta", tenant_id),
            "tau": BrainSetting.get("tau", tenant_id),
            "sparsity": BrainSetting.get("gmd_sparsity", tenant_id),
        }
    }
