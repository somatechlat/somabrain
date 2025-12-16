"""Health Helpers - Helper functions for health endpoints.

Extracted from somabrain/routers/health.py per vibe-compliance-audit spec.
Provides lazy accessors and utility functions for health checks.
"""

from __future__ import annotations

import urllib.request
from typing import Any, Dict, Optional

from common.config.settings import settings
from somabrain import metrics as M


def get_runtime():
    """Lazy import of runtime module to access singletons."""
    import importlib.util
    import os
    import sys

    _runtime_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "runtime.py")
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


def get_app_config():
    """Get the application configuration."""
    return settings


def get_mt_memory():
    """Get the multi-tenant memory singleton."""
    rt = get_runtime()
    if rt:
        return getattr(rt, "mt_memory", None)
    return None


def get_embedder():
    """Get the embedder singleton."""
    rt = get_runtime()
    if rt:
        return getattr(rt, "embedder", None)
    return None


def get_app_state():
    """Get the FastAPI app state for OPA engine access."""
    try:
        from somabrain.app import app

        return app.state
    except Exception:
        return None


def ping(url: str) -> bool:
    """Ping a URL and return True if it responds with 2xx."""
    ping_timeout = float(getattr(settings, "health_ping_timeout", 0.5) or 0.5)
    try:
        with urllib.request.urlopen(url, timeout=ping_timeout) as r:  # noqa: S310
            return 200 <= getattr(r, "status", 500) < 300
    except Exception:
        return False


def milvus_metrics_for_tenant(tenant_id: str) -> Dict[str, Optional[float]]:
    """Return Milvus telemetry (p95 latencies + segment load) for a tenant."""

    def _read(gauge, **labels) -> Optional[float]:
        try:
            child = gauge.labels(**labels)
            stored = getattr(child, "_value", None)
            if stored is None:
                return None
            return float(stored.get())
        except Exception:
            return None

    return {
        "search_latency_p95_seconds": _read(M.MILVUS_SEARCH_LAT_P95, tenant_id=tenant_id),
        "ingest_latency_p95_seconds": _read(M.MILVUS_INGEST_LAT_P95, tenant_id=tenant_id),
        "segment_load": _read(
            M.MILVUS_SEGMENT_LOAD,
            collection=getattr(settings, "milvus_collection", "oak_options"),
        ),
    }
