"""Health Router - Health check, metrics, and diagnostics endpoints."""

from __future__ import annotations

import logging
import urllib.request
from typing import Any, Dict

from fastapi import APIRouter, Request

from common.config.settings import settings
from somabrain import metrics as M
from somabrain.version import API_VERSION

logger = logging.getLogger(__name__)
router = APIRouter(tags=["health"])


def _get_runtime_singletons():
    from somabrain import runtime as rt
    return rt


def _get_app_config():
    rt = _get_runtime_singletons()
    return getattr(rt, "cfg", settings)


def _ping(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=0.5) as r:
            return 200 <= getattr(r, "status", 500) < 300
    except Exception:
        return False


def _milvus_metrics_for_tenant(tenant_id: str) -> Dict[str, Any]:
    try:
        return {
            "ingest_p95_ms": M.MILVUS_INGEST_P95.labels(tenant_id=tenant_id)._value.get(),
            "search_p95_ms": M.MILVUS_SEARCH_P95.labels(tenant_id=tenant_id)._value.get(),
            "segment_load": M.MILVUS_SEGMENT_LOAD.labels(tenant_id=tenant_id)._value.get(),
        }
    except Exception:
        return {"ingest_p95_ms": None, "search_p95_ms": None, "segment_load": None}


@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return await M.metrics_endpoint()


@router.get("/healthz", include_in_schema=False)
async def healthz(request: Request) -> dict:
    """Alias for /health."""
    return {"ok": True}


@router.get("/diagnostics", include_in_schema=False)
async def diagnostics() -> dict:
    """Lightweight diagnostics."""
    cfg = _get_app_config()
    return {
        "in_container": settings.running_in_docker,
        "mode": settings.mode.strip() or "",
        "external_backends_required": settings.require_external_backends,
        "require_memory": settings.require_memory,
        "api_version": int(API_VERSION),
    }

