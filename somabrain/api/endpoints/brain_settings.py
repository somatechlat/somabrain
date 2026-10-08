"""Brain Settings Management API - Persona-Driven implementation.

Features:
- Namespace isolation on ``tenant_id`` (data-partition key only)
- Bearer authentication via ``api_key_auth`` (Vault-managed token)
- Zero-latency cognitive shifts
"""

from typing import Any

from django.http import HttpRequest
from ninja import Router, Schema

from somabrain.api.auth import api_key_auth, bind_credential_tenant
from somabrain.brain_settings.models import BrainSetting
from somabrain.brain_settings.modes import BRAIN_MODES

router = Router(tags=["Brain Settings"])


class ModeResponse(Schema):
    mode: str
    description: str
    parameters: dict[str, Any]


class SetModeSchema(Schema):
    mode: str


class SettingPutSchema(Schema):
    key: str
    value: Any


class SettingResponse(Schema):
    key: str
    value: Any
    category: str
    learnable: bool
    min: float | None = None
    max: float | None = None
    type: str | None = None


@router.get("/modes", auth=api_key_auth, response=list[ModeResponse])
def list_brain_modes(request: HttpRequest):
    """List all available cognitive operational modes."""
    return [
        {"mode": k, "description": v["description"], "parameters": v["overrides"]}
        for k, v in BRAIN_MODES.items()
    ]


@router.post("/mode", auth=api_key_auth)
def set_brain_mode(request: HttpRequest, data: SetModeSchema):
    """
    Atomic cognitive shift. Immediate cache invalidation.
    Persona: Django Architect / Security Auditor
    """
    tenant_id = bind_credential_tenant(request)
    mode = data.mode.upper()

    if mode not in BRAIN_MODES:
        from ninja.errors import HttpError

        raise HttpError(
            400, f"Invalid mode '{mode}'. Available: {list(BRAIN_MODES.keys())}"
        )

    # Atomic DB update with cache invalidation
    BrainSetting.set("active_brain_mode", mode, tenant=tenant_id)

    return {
        "status": "success",
        "tenant_id": tenant_id,
        "new_mode": mode,
        "description": BRAIN_MODES[mode]["description"],
    }


@router.get("/status", auth=api_key_auth)
def get_brain_status(request: HttpRequest):
    """Get current operational state and critical GMD knobs."""
    tenant_id = bind_credential_tenant(request)

    return {
        "active_mode": BrainSetting.get("active_brain_mode", tenant_id),
        "knobs": {
            "gmd_eta": BrainSetting.get("gmd_eta", tenant_id),
            "tau": BrainSetting.get("tau", tenant_id),
            "sparsity": BrainSetting.get("gmd_sparsity", tenant_id),
        },
    }


@router.get("/settings", auth=api_key_auth)
def list_settings(request: HttpRequest) -> dict[str, Any]:
    """List all administerable BrainSetting knobs (system-role UI)."""
    from somabrain.brain_settings.models import BRAIN_DEFAULTS

    tenant_id = bind_credential_tenant(request)
    items = []
    for key, meta in BRAIN_DEFAULTS.items():
        try:
            value = BrainSetting.get(key, tenant_id)
        except Exception:
            value = meta.get("v")
        items.append(
            {
                "key": key,
                "value": value,
                "category": meta.get("cat", ""),
                "learnable": bool(meta.get("learnable", False)),
                "min": meta.get("min"),
                "max": meta.get("max"),
                "type": meta.get("type"),
            }
        )
    return {"tenant_id": tenant_id, "settings": items}


@router.put("/settings", auth=api_key_auth)
def put_setting(request: HttpRequest, data: SettingPutSchema) -> dict[str, Any]:
    """Administer one BrainSetting knob. Validates bounds. Tenant from credential."""
    from ninja.errors import HttpError

    from somabrain.brain_settings.models import BRAIN_DEFAULTS

    tenant_id = bind_credential_tenant(request)
    key = data.key
    if key not in BRAIN_DEFAULTS:
        raise HttpError(404, f"Unknown setting key '{key}'")
    meta = BRAIN_DEFAULTS[key]
    value = data.value

    # Bound validation for numeric knobs
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        lo, hi = meta.get("min"), meta.get("max")
        if lo is not None and value < lo:
            raise HttpError(422, f"{key}={value} below min {lo}")
        if hi is not None and value > hi:
            raise HttpError(422, f"{key}={value} above max {hi}")
        if not isinstance(value, (int, float)):
            raise HttpError(422, f"{key} must be numeric")

    try:
        BrainSetting.set(key, value, tenant=tenant_id)
    except Exception as exc:
        raise HttpError(500, f"failed to persist {key}: {exc}") from exc

    return {
        "key": key,
        "value": BrainSetting.get(key, tenant_id),
        "tenant_id": tenant_id,
        "learnable": bool(meta.get("learnable", False)),
    }
