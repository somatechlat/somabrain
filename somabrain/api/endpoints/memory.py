"""Memory API - Django Ninja Version

Migrated from FastAPI to Django Ninja.
Memory recall, storage, and management endpoints.

CANONICAL CONTRACT (see ``somabrain.api.memory.models`` for the shapes):

* ``POST /api/memory/remember`` — write (alias ``/memory/remember``)
* ``POST /api/memory/recall``   — read  (alias ``/memory/recall``)
* ``POST /api/memory/forget``   — delete (alias ``/memory/forget``)

``/api/memory/*`` and ``/memory/*`` are the same handlers (the NinjaAPI is
dual-mounted in ``somabrain.config.urls``); ``/api/remember`` and friends are
thin aliases registered in ``somabrain.api.v1`` for the legacy BrainBridge
dialect. There is exactly one implementation behind all of them.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx
from django.conf import settings
from django.http import HttpRequest
from ninja import Router
from ninja.errors import HttpError
from pydantic import BaseModel, Field, model_validator

from somabrain.api.auth import api_key_auth, require_auth
from somabrain.api.memory.helpers import (
    _as_float_list,
    _resolve_namespace,
    _serialize_coord,
)
from somabrain.api.memory.models import ForgetRequest, ForgetResponse, _iso_created_at
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


def _get_embedder():
    """Get the runtime semantic embedder (SomaBrain)."""
    from somabrain.runtime.manager import get_embedder

    return get_embedder()


def _evict_wm_coord(wm: Any, tenant: str, coord_list: list) -> int:
    """Remove WM items whose stored coordinate matches ``coord_list``."""
    target = tuple(float(x) for x in coord_list)
    removed = 0
    store = getattr(wm, "_wms", {}).get(tenant) if hasattr(wm, "_wms") else None
    if store is None:
        return 0
    items = getattr(store, "_items", None)
    if items is None:
        return 0
    keep = []
    for it in items:
        payload = getattr(it, "payload", None) or {}
        raw = payload.get("coordinate") or payload.get("coord")
        if isinstance(raw, str):
            try:
                raw = [float(x) for x in raw.split(",")]
            except Exception:
                raw = None
        if isinstance(raw, (list, tuple)) and len(raw) == 3:
            if tuple(float(x) for x in raw) == target:
                removed += 1
                continue
        keep.append(it)
    store._items = keep
    return removed


def _hit_text(payload: Any) -> str:
    """Extract the primary text from a stored memory payload."""
    if not isinstance(payload, dict):
        return "" if payload is None else str(payload)
    for key in ("text", "task", "content", "what", "fact", "headline", "description"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
        if isinstance(value, dict):
            nested = value.get("text") or value.get("task") or value.get("content")
            if isinstance(nested, str) and nested.strip():
                return nested
    return ""


def _hit_record(
    payload: Any, score: float, layer: str, coord_list: list[float] | None
) -> dict:
    """Build one MemoryHit-shaped result plus its legacy aliases."""
    payload_dict = payload if isinstance(payload, dict) else {"content": payload}
    coord_str = (
        f"{coord_list[0]},{coord_list[1]},{coord_list[2]}" if coord_list else None
    )
    return {
        # seam MemoryHit fields
        "text": _hit_text(payload_dict),
        "coord": coord_str,
        "score": float(score),
        "store": "somabrain" if layer == "wm" else "somafractalmemory",
        "created_at": _iso_created_at(payload_dict),
        # legacy aliases
        "content": payload,
        "layer": layer,
        "coordinate": coord_list,
    }


class RecallRequest(BaseModel):
    """Recall request — accepts ``top_k`` or ``k``, ``tenant`` or ``tenant_id``."""

    query: str = Field(..., description="Query text")
    top_k: int = Field(10, description="Max results")
    layer: str = Field("both", description="wm, ltm, or both")
    tenant: str | None = None
    tenant_id: str | None = Field(None, description="Seam alias for tenant")
    namespace: str | None = None
    universe: str | None = Field(None, description="Optional universe scope")
    k: int | None = Field(None, description="Seam/legacy alias for top_k")

    @model_validator(mode="before")
    @classmethod
    def _normalize_aliases(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        d = dict(data)
        if d.get("top_k") is None and d.get("k") is not None:
            d["top_k"] = d["k"]
        if not d.get("tenant") and d.get("tenant_id"):
            d["tenant"] = d["tenant_id"]
        return d


@router.post("/recall", auth=api_key_auth)
async def recall_memory(request: HttpRequest, payload: RecallRequest):
    """Unified recall endpoint backed by the real memory backend.

    Returns seam ``MemoryHit`` items (``text/coord/score/store/created_at``)
    in ``results``; the legacy ``content/layer/coordinate`` keys are kept on
    each item as aliases.
    """
    ctx = await get_tenant(request, getattr(settings, "NAMESPACE", "default"))
    require_auth(request, settings)

    pool = _get_memory_pool()
    if not pool:
        raise HttpError(503, "Memory pool not available")

    namespace = payload.namespace or ctx.namespace
    # Tenant scoping: the request body's tenant wins so a remembered item is
    # recallable with the same tenant_id even when the X-Tenant-ID header is
    # absent (the seam carries tenant on every call, not only in headers).
    tenant = (payload.tenant or payload.tenant_id or ctx.tenant_id or "").strip()
    tenant = tenant or ctx.tenant_id
    # Same fully-qualified namespace as the remember path so recall reads the
    # representation that was written (one write path, one read path).
    memsvc = MemoryService(pool, _resolve_namespace(tenant, namespace))

    top_k = max(1, int(payload.top_k or payload.k or 10))
    layer = payload.layer or "both"
    universe = payload.universe or request.headers.get("X-Universe")

    t0 = time.perf_counter()
    results = []
    wm_hits = 0
    ltm_hits = 0
    degraded = False
    degraded_reasons: list[str] = []

    def _tenant_match(hit_payload: dict | None) -> bool:
        """Drop LTM hits that belong to a different tenant/namespace.

        Tenant is the isolation boundary and is always enforced. Namespace is
        an opt-in refinement: it is only compared when the caller set
        ``namespace`` explicitly on the request, so a seam-shaped call (which
        has no namespace field) still sees what it wrote under the default.
        """
        if not isinstance(hit_payload, dict):
            return True
        hit_tenant = hit_payload.get("tenant") or hit_payload.get("tenant_id")
        hit_namespace = hit_payload.get("namespace")
        if hit_tenant and hit_tenant != tenant:
            return False
        if hit_namespace and payload.namespace and hit_namespace != payload.namespace:
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
                coord_list = _serialize_coord(coord) or _as_float_list(
                    (payload_data or {}).get("coordinate")
                    if isinstance(payload_data, dict)
                    else None
                )
                results.append(
                    _hit_record(
                        payload_data,
                        float(score) if isinstance(score, (int, float)) else 0.0,
                        "ltm",
                        coord_list,
                    )
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

    # 2) Add working-memory items when requested — semantic score vs query,
    #    never a hardcoded 1.0 dump (that would crush LTM ranking).
    if layer in ("wm", "both"):
        wm = _get_wm()
        if wm:
            try:
                query_vec = None
                try:
                    embedder = _get_embedder()
                    if embedder is not None:
                        query_vec = embedder.embed(payload.query)
                except Exception:
                    query_vec = None

                if query_vec is not None:
                    scored_wm = wm.recall(tenant, query_vec, top_k)
                    wm_hits = len(scored_wm)
                    for score, item in scored_wm[:top_k]:
                        item_payload = (
                            item if isinstance(item, dict) else {"content": item}
                        )
                        results.append(
                            _hit_record(
                                item,
                                float(score),
                                "wm",
                                _as_float_list(item_payload.get("coordinate")),
                            )
                        )
                else:
                    wm_items = wm.items(tenant, limit=top_k)
                    wm_hits = len(wm_items)
                    for item in wm_items[:top_k]:
                        item_payload = (
                            item if isinstance(item, dict) else {"content": item}
                        )
                        results.append(
                            _hit_record(
                                item,
                                0.0,
                                "wm",
                                _as_float_list(item_payload.get("coordinate")),
                            )
                        )
            except Exception as exc:
                logger.warning("WM recall failed: %s", exc)

    # Sort combined results by score descending and apply top_k limit
    results.sort(key=lambda r: r.get("score", 0.0), reverse=True)
    results = results[:top_k]

    dt_ms = round((time.perf_counter() - t0) * 1000.0, 3)

    return {
        "tenant": tenant,
        "namespace": namespace,
        "results": results,
        "wm_hits": wm_hits,
        "ltm_hits": ltm_hits,
        "duration_ms": dt_ms,
        "total_results": len(results),
        "degraded": degraded,
        "degraded_reasons": degraded_reasons,
    }


@router.post("/forget", response=ForgetResponse, auth=api_key_auth)
async def forget_memory(request: HttpRequest, payload: ForgetRequest):
    """Delete the memory at ``coord`` (seam ``MemoryGateway.forget``).

    Fails closed: a backend outage surfaces as an HTTP error, never as a
    silent success. ``ok: false`` with an ``error`` is returned only when the
    coordinate is not present.
    """
    ctx = await get_tenant(request, getattr(settings, "NAMESPACE", "default"))
    require_auth(request, settings)

    tenant = (payload.tenant or payload.tenant_id or ctx.tenant_id or "").strip()
    tenant = tenant or ctx.tenant_id
    namespace = ctx.namespace

    coord_list = _as_float_list(payload.coord)
    if coord_list is None:
        raise HttpError(400, f"invalid coord: {payload.coord!r}")
    coord_str = f"{coord_list[0]},{coord_list[1]},{coord_list[2]}"

    pool = _get_memory_pool()
    if not pool:
        raise HttpError(503, "Memory pool not available")

    memsvc = MemoryService(pool, _resolve_namespace(tenant, namespace))
    memsvc._reset_circuit_if_needed()

    try:
        deleted = await memsvc.adelete(tuple(coord_list))
    except AttributeError as exc:
        # Older backends without delete support must not silently no-op.
        raise HttpError(501, f"memory backend cannot delete: {exc}") from exc
    except (httpx.HTTPError, MemoryServiceError, RuntimeError) as exc:
        raise _map_memory_error(exc) from exc
    except Exception as exc:
        logger.exception("forget failed for coord=%s: %s", coord_str, exc)
        raise HttpError(500, f"forget failed: {exc}") from exc

    # Also evict from working memory so recall cannot resurrect a forgotten row.
    wm_removed = 0
    wm = _get_wm()
    if wm is not None:
        try:
            wm_removed = _evict_wm_coord(wm, tenant, coord_list)
        except Exception as exc:
            logger.warning("WM evict failed for coord=%s: %s", coord_str, exc)

    ok = bool(deleted) or wm_removed > 0
    return {
        "ok": ok,
        "coord": coord_str,
        "store": "somafractalmemory",
        "tenant": tenant,
        "error": None if ok else "not found",
    }


@router.get("/metrics", auth=api_key_auth)
def memory_metrics(
    request: HttpRequest, tenant: str | None = None, namespace: str | None = None
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
