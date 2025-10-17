"""Config API (No-Kong edition).

Exposes effective config reads and patch endpoints backed by the in-process
ConfigService. This is a minimal, real implementation to unblock end-to-end
tests without introducing external dependencies.
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Body, HTTPException, Query, Request
from pydantic import BaseModel

from somabrain.config import Config
from somabrain.services.config_service import (
    ConfigMergeError,
    ConfigService,
)


router = APIRouter(prefix="/config", tags=["config"])


# Singleton service for this process
_config_service = ConfigService(lambda: Config())


class EffectiveConfigResponse(BaseModel):
    tenant: str
    namespace: str
    config: Dict[str, Any]


@router.get("/memory", response_model=EffectiveConfigResponse)
async def get_memory_config(
    tenant: str = Query("", description="Tenant id"),
    namespace: str = Query("", description="Namespace (e.g., wm, ltm)"),
):
    cfg = _config_service.effective_config(tenant, namespace)
    return EffectiveConfigResponse(tenant=tenant, namespace=namespace, config=cfg)


@router.patch("/memory")
async def patch_memory_config(
    request: Request,
    tenant: str = Query(..., description="Tenant id"),
    namespace: str = Query(..., description="Namespace"),
    payload: Dict[str, Any] = Body(..., description="Partial config patch"),
):
    actor = request.headers.get("X-Actor") or "api"
    try:
        await _config_service.patch_namespace(tenant, namespace, payload, actor=actor)
    except ConfigMergeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=f"config patch failed: {exc}")
    cfg = _config_service.effective_config(tenant, namespace)
    return {"ok": True, "tenant": tenant, "namespace": namespace, "config": cfg}
