"""Config API (No-Kong edition).

Exposes effective config reads and patch endpoints backed by the in-process
ConfigService. This is a minimal, real implementation to unblock end-to-end
tests without introducing external dependencies.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException, Query, Request
from pydantic import BaseModel

from somabrain.runtime.config_runtime import (
    ensure_config_dispatcher,
    get_config_service,
    get_cutover_controller,
)
from somabrain.services.config_service import ConfigMergeError
from somabrain.services.cutover_controller import CutoverError, CutoverPlan


router = APIRouter(prefix="/config", tags=["config"])


# Singleton service for this process
_config_service = get_config_service()
_cutover_controller = get_cutover_controller()


class EffectiveConfigResponse(BaseModel):
    tenant: str
    namespace: str
    config: Dict[str, Any]


class CutoverOpenRequest(BaseModel):
    tenant: str
    from_namespace: str
    to_namespace: str


class CutoverMetricsRequest(BaseModel):
    tenant: str
    namespace: str
    top1_accuracy: float
    margin: float
    latency_p95_ms: float


class CutoverTenantRequest(BaseModel):
    tenant: str
    reason: Optional[str] = None


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
    try:
        await ensure_config_dispatcher()
        await _config_service.patch_namespace(tenant, namespace, payload, actor=actor)
    except ConfigMergeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=500, detail=f"config patch failed: {exc}")
    cfg = _config_service.effective_config(tenant, namespace)
    return {"ok": True, "tenant": tenant, "namespace": namespace, "config": cfg}


@router.post("/cutover/open")
async def open_cutover(payload: CutoverOpenRequest):
    try:
        await ensure_config_dispatcher()
        plan = await _cutover_controller.open_plan(
            payload.tenant,
            payload.from_namespace,
            payload.to_namespace,
        )
    except CutoverError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True, "plan": _plan_to_dict(plan)}


@router.post("/cutover/metrics")
async def record_cutover_metrics(payload: CutoverMetricsRequest):
    try:
        await ensure_config_dispatcher()
        plan = await _cutover_controller.record_shadow_metrics(
            payload.tenant,
            payload.namespace,
            top1_accuracy=payload.top1_accuracy,
            margin=payload.margin,
            latency_p95_ms=payload.latency_p95_ms,
        )
    except CutoverError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True, "plan": _plan_to_dict(plan)}


@router.post("/cutover/approve")
async def approve_cutover(payload: CutoverTenantRequest):
    try:
        await ensure_config_dispatcher()
        plan = await _cutover_controller.approve(payload.tenant)
    except CutoverError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True, "plan": _plan_to_dict(plan)}


@router.post("/cutover/execute")
async def execute_cutover(payload: CutoverTenantRequest):
    try:
        await ensure_config_dispatcher()
        plan = await _cutover_controller.execute(payload.tenant)
    except CutoverError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True, "plan": _plan_to_dict(plan)}


@router.post("/cutover/cancel")
async def cancel_cutover(payload: CutoverTenantRequest):
    try:
        await ensure_config_dispatcher()
        await _cutover_controller.cancel(payload.tenant, reason=payload.reason or "")
    except CutoverError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"ok": True}


def _plan_to_dict(plan: CutoverPlan) -> Dict[str, Any]:
    data: Dict[str, Any] = {
        "tenant": plan.tenant,
        "from_namespace": plan.from_namespace,
        "to_namespace": plan.to_namespace,
        "status": plan.status,
        "ready": plan.ready,
        "created_at": plan.created_at,
        "approved_at": plan.approved_at,
        "notes": list(plan.notes),
    }
    if plan.last_shadow_metrics is not None:
        metrics = plan.last_shadow_metrics
        data["last_shadow_metrics"] = {
            "top1_accuracy": metrics.top1_accuracy,
            "margin": metrics.margin,
            "latency_p95_ms": metrics.latency_p95_ms,
            "collected_at": metrics.collected_at,
        }
    return data
