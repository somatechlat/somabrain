"""Config API (No-Kong edition).

Exposes effective config reads and patch endpoints backed by the in-process
ConfigService. This is a minimal, real implementation to unblock end-to-end
tests without introducing external dependencies.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Body, HTTPException, Query, Request
from pydantic import BaseModel

from somabrain.runtime.config_runtime import (
    ensure_config_dispatcher,
    get_config_service,
)
from somabrain.services.config_service import ConfigMergeError


router = APIRouter(prefix="/config", tags=["config"])


# Singleton service for this process
_config_service = get_config_service()


class EffectiveConfigResponse(BaseModel):
    tenant: str
    namespace: str
    config: Dict[str, Any]


# Cutover request/response models have been removed per VIBE hardening.


@router.get("/memory", response_model=EffectiveConfigResponse)
async def get_memory_config(
    tenant: str = Query("", description="Tenant id"),
    namespace: str = Query("", description="Namespace (e.g., wm, ltm)"),
):
    await ensure_config_dispatcher()
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
    # Cutover functionality has been removed per VIBE hardening.
    await ensure_config_dispatcher()
