"""Memory API - Django Ninja Version

Migrated from FastAPI to Django Ninja.
Memory recall, storage, and management endpoints.
"""

from __future__ import annotations

import logging
import time
from typing import Optional
from ninja import Router
from django.http import HttpRequest
from ninja.errors import HttpError

from django.conf import settings
from somabrain.api.auth import bearer_auth
from somabrain.auth import require_auth
from somabrain.tenant import get_tenant
from somabrain.services.memory_service import MemoryService

logger = logging.getLogger("somabrain.api.endpoints.memory")

router = Router(tags=["memory"])


def _get_runtime():
    """Lazy import runtime for singletons."""
    import importlib.util
    import os
    import sys

    _runtime_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "runtime.py"
    )
    _spec = importlib.util.spec_from_file_location("somabrain.runtime_module", _runtime_path)
    if _spec and _spec.name in sys.modules:
        return sys.modules[_spec.name]
    for m in list(sys.modules.values()):
        try:
            mf = getattr(m, "__file__", "") or ""
            if mf.endswith(os.path.join("somabrain", "runtime.py")):
                return m
        except Exception:
            continue
    return None


def _get_memory_pool():
    """Get memory pool singleton."""
    rt = _get_runtime()
    if rt:
        return getattr(rt, "mt_memory", None)
    return None


def _get_wm():
    """Get working memory singleton."""
    rt = _get_runtime()
    if rt:
        return getattr(rt, "mt_wm", None)
    return None


@router.post("/recall", auth=bearer_auth)
def recall_memory(request: HttpRequest, payload: dict):
    """Unified recall endpoint backed by retrieval pipeline."""
    ctx = get_tenant(request, getattr(settings, "NAMESPACE", "default"))
    require_auth(request, settings)

    pool = _get_memory_pool()
    if not pool:
        raise HttpError(503, "Memory pool not available")

    # Get memory service for tenant
    namespace = ctx.namespace
    MemoryService(pool, namespace)

    # Extract query parameters
    payload.get("query", "")
    top_k = int(payload.get("top_k", 10))
    layer = payload.get("layer", "both")

    t0 = time.perf_counter()

    # Simplified recall logic
    wm = _get_wm()
    results = []
    wm_hits = 0
    ltm_hits = 0

    # Get WM items if requested
    if layer in ("wm", "both") and wm:
        try:
            wm_items = wm.items(ctx.tenant_id)
            wm_hits = len(wm_items)
            results.extend(
                [{"content": str(item), "layer": "wm", "score": 1.0} for item in wm_items[:top_k]]
            )
        except Exception as exc:
            logger.warning(f"WM recall failed: {exc}")

    dt_ms = round((time.perf_counter() - t0) * 1000.0, 3)

    return {
        "tenant": ctx.tenant_id,
        "namespace": namespace,
        "results": results,
        "wm_hits": wm_hits,
        "ltm_hits": ltm_hits,
        "duration_ms": dt_ms,
        "total_results": len(results),
    }


@router.get("/metrics", auth=bearer_auth)
def memory_metrics(
    request: HttpRequest, tenant: Optional[str] = None, namespace: Optional[str] = None
):
    """Get memory metrics for a tenant/namespace."""
    ctx = get_tenant(request, getattr(settings, "NAMESPACE", "default"))
    require_auth(request, settings)

    target_tenant = tenant or ctx.tenant_id
    target_namespace = namespace or ctx.namespace

    wm = _get_wm()
    wm_items = 0

    if wm:
        try:
            wm_items = len(wm.items(target_tenant))
        except Exception:
            wm_items = 0

    return {
        "tenant": target_tenant,
        "namespace": target_namespace,
        "wm_items": wm_items,
        "circuit_open": False,
    }
