"""Memory API - Django Ninja Version

Migrated from FastAPI to Django Ninja.
Memory recall, storage, and management endpoints.
"""

from __future__ import annotations

import logging
import time
from typing import List, Optional

import httpx
from django.conf import settings
from django.http import HttpRequest
from ninja import Router
from ninja.errors import HttpError

from pydantic import BaseModel, Field

from somabrain.api.auth import api_key_auth
from somabrain.api.memory.helpers import _serialize_coord
from somabrain.api.auth import require_auth
from somabrain.core.exceptions import CircuitBreakerOpen, MemoryServiceError
from somabrain.services.memory_service import MemoryService
from somabrain.tenant import get_tenant, get_tenant_sync

logger = logging.getLogger("somabrain.api.endpoints.memory")

router = Router(tags=["memory"])


def _map_memory_error(exc: Exception) -> HttpError:
    """Map a memory backend exception to an HTTP error response."""
    if isinstance(exc, httpx.TimeoutException):
        return HttpError(504, "memory backend timeout")
    if isinstance(exc, httpx.ConnectError):
        return HttpError(503, "memory backend unreachable")
    if isinstance(exc, httpx.HTTPStatusError):
        return HttpError(502, f"memory backend error: {exc.response.status_code}")
    if isinstance(exc, CircuitBreakerOpen):
        return HttpError(503, str(exc))
    if isinstance(exc, MemoryServiceError):
        return HttpError(502, str(exc))
    if isinstance(exc, RuntimeError):
        return HttpError(503, str(exc))
    return HttpError(500, f"unexpected memory error: {exc}")


def _get_memory_pool():
    """Get memory pool singleton."""
    from somabrain.runtime import get_memory_pool

    return get_memory_pool()


def _get_wm():
    """Get working memory singleton."""
    from somabrain.runtime import get_working_memory

    return get_working_memory()


class RecallRequest(BaseModel):
    query: str = Field(..., description="Query text")
    top_k: int = Field(10, description="Max results")
    layer: str = Field("both", description="wm, ltm, or both")
    tenant: Optional[str] = None
    namespace: Optional[str] = None
    universe: Optional[str] = Field(None, description="Optional universe scope")


@router.post("/recall", auth=api_key_auth)
async def recall_memory(request: HttpRequest, payload: RecallRequest):
    """Unified recall endpoint backed by the real memory backend."""
    ctx = await get_tenant(request, getattr(settings, "NAMESPACE", "default"))
    require_auth(request, settings)

    pool = _get_memory_pool()
    if not pool:
        raise HttpError(503, "Memory pool not available")

    namespace = ctx.namespace
    memsvc = MemoryService(pool, namespace)

    top_k = max(1, int(payload.top_k))
    layer = payload.layer or "both"
    universe = payload.universe or request.headers.get("X-Universe")

    t0 = time.perf_counter()
    results = []
    wm_hits = 0
    ltm_hits = 0
    degraded = False
    degraded_reasons: List[str] = []

    def _tenant_match(hit_payload: dict | None) -> bool:
        """Drop LTM hits that belong to a different tenant/namespace."""
        if not isinstance(hit_payload, dict):
            return True
        hit_tenant = hit_payload.get("tenant") or hit_payload.get("tenant_id")
        hit_namespace = hit_payload.get("namespace")
        if hit_tenant and hit_tenant != ctx.tenant_id:
            return False
        if hit_namespace and hit_namespace != namespace:
            return False
        return True

    # 1) Query long-term memory via SFM when requested
    if layer in ("ltm", "both"):
        try:
            hits = await memsvc.arecall(payload.query, top_k=top_k, universe=universe)
            filtered_hits = []
            for hit in hits:
                payload_data = (
                    hit.get("payload")
                    if isinstance(hit, dict)
                    else getattr(hit, "payload", None)
                )
                if _tenant_match(payload_data):
                    filtered_hits.append(hit)
            ltm_hits = len(filtered_hits)
            for hit in filtered_hits[:top_k]:
                payload_data = (
                    hit.get("payload")
                    if isinstance(hit, dict)
                    else getattr(hit, "payload", None)
                )
                score = (
                    hit.get("score")
                    if isinstance(hit, dict)
                    else getattr(hit, "score", None)
                )
                coord = (
                    hit.get("coordinate")
                    if isinstance(hit, dict)
                    else getattr(hit, "coordinate", None)
                )
                results.append(
                    {
                        "content": payload_data,
                        "layer": "ltm",
                        "score": float(score) if isinstance(score, (int, float)) else 1.0,
                        "coordinate": _serialize_coord(coord),
                    }
                )
        except (httpx.HTTPError, MemoryServiceError, RuntimeError) as exc:
            logger.warning("LTM recall failed for namespace=%s: %s", namespace, exc)
            if layer == "ltm":
                raise _map_memory_error(exc) from exc
            degraded = True
            degraded_reasons.append(f"ltm: {exc}")
        except Exception as exc:
            logger.exception("LTM recall failed for namespace=%s: %s", namespace, exc)
            if layer == "ltm":
                raise HttpError(500, f"ltm recall unavailable: {exc}") from exc
            degraded = True
            degraded_reasons.append(f"ltm: {exc}")

    # 2) Add working-memory items when requested
    if layer in ("wm", "both"):
        wm = _get_wm()
        if wm:
            try:
                wm_items = wm.items(ctx.tenant_id)
                wm_hits = len(wm_items)
                results.extend(
                    [
                        {"content": item, "layer": "wm", "score": 1.0}
                        for item in wm_items[:top_k]
                    ]
                )
            except Exception as exc:
                logger.warning("WM recall failed: %s", exc)

    # Sort combined results by score descending and apply top_k limit
    results.sort(key=lambda r: r.get("score", 0.0), reverse=True)
    results = results[:top_k]

    dt_ms = round((time.perf_counter() - t0) * 1000.0, 3)

    return {
        "tenant": ctx.tenant_id,
        "namespace": namespace,
        "results": results,
        "wm_hits": wm_hits,
        "ltm_hits": ltm_hits,
        "duration_ms": dt_ms,
        "total_results": len(results),
        "degraded": degraded,
        "degraded_reasons": degraded_reasons,
    }


@router.get("/metrics", auth=api_key_auth)
def memory_metrics(
    request: HttpRequest, tenant: Optional[str] = None, namespace: Optional[str] = None
):
    """Get real memory metrics for a tenant/namespace."""
    ctx = get_tenant_sync(request, getattr(settings, "NAMESPACE", "default"))
    require_auth(request, settings)

    target_tenant = tenant or ctx.tenant_id
    target_namespace = namespace or ctx.namespace

    pool = _get_memory_pool()
    memsvc = MemoryService(pool, target_namespace) if pool else None

    wm = _get_wm()
    wm_items = 0
    if wm:
        try:
            wm_items = len(wm.items(target_tenant))
        except Exception:
            wm_items = 0

    circuit_open = False
    if memsvc is not None:
        try:
            state = memsvc.get_circuit_state()
            circuit_open = bool(state.get("open", False))
        except Exception:
            circuit_open = False

    return {
        "tenant": target_tenant,
        "namespace": target_namespace,
        "wm_items": wm_items,
        "circuit_open": circuit_open,
    }
