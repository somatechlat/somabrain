"""Health Helpers - Helper functions for health endpoints.

Migrated from somabrain/routers/health_helpers.py.
Provides lazy accessors and utility functions for health checks.
"""

from __future__ import annotations

import urllib.request

from django.conf import settings

from somabrain import metrics as M


def get_runtime():
    """Lazy import of runtime module to access singletons."""
    import importlib.util
    import os
    import sys

    # Assuming runtime.py is in somabrain root
    # __file__ is somabrain/health/helpers.py, so up 2 levels
    _runtime_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "runtime.py"
    )
    _spec = importlib.util.spec_from_file_location(
        "somabrain.runtime_module", _runtime_path
    )
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


# Module-level singletons for lazy initialization (Django pattern)
_cached_embedder = None
_cached_mt_memory = None


def get_mt_memory():
    """Get the multi-tenant memory singleton or verify SFM is reachable.

    Uses Django bootstrap pattern instead of runtime.py loading.
    Per VIBE rules: real implementations, no stubs.

    For health checks, we verify SFM is reachable via /healthz endpoint.
    """
    global _cached_mt_memory
    if _cached_mt_memory is not None:
        return _cached_mt_memory

    # First try runtime module (if loaded by other code)
    rt = get_runtime()
    if rt:
        _cached_mt_memory = getattr(rt, "mt_memory", None)
        if _cached_mt_memory is not None:
            return _cached_mt_memory

    # Fallback: verify SFM is reachable for health checks
    try:
        memory_endpoint = getattr(settings, "SOMABRAIN_MEMORY_HTTP_ENDPOINT")
        if memory_endpoint:
            # Ping SFM healthz endpoint to verify it's reachable
            healthz_url = memory_endpoint.rstrip("/") + "/healthz"
            if ping(healthz_url):
                # Return a non-None marker to indicate SFM is available
                # Actual MultiTenantMemory is created by runtime.py at startup
                return {"sfm_endpoint": memory_endpoint, "status": "reachable"}
    except Exception:
        pass

    return None


def get_embedder():
    """Get the embedder singleton.

    Uses Django bootstrap pattern with lazy initialization.
    Per VIBE rules: real implementations, no stubs.
    """
    global _cached_embedder
    if _cached_embedder is not None:
        return _cached_embedder

    # First try runtime module (if loaded by other code)
    rt = get_runtime()
    if rt:
        _cached_embedder = getattr(rt, "embedder", None)
        if _cached_embedder is not None:
            return _cached_embedder

    # Fallback: create via Django bootstrap factories
    try:
        from somabrain.bootstrap.singletons import make_embedder_with_dim

        embedder, _ = make_embedder_with_dim(settings, quantum=None)
        _cached_embedder = embedder
        return _cached_embedder
    except Exception:
        pass

    return None


def ping(url: str) -> bool:
    """Ping a URL and return True if it responds with 2xx."""
    ping_timeout = float(getattr(settings, "HEALTH_PING_TIMEOUT") or 0.5)
    try:
        with urllib.request.urlopen(url, timeout=ping_timeout) as r:
            return 200 <= getattr(r, "status", 500) < 300
    except Exception:
        return False


def check_cognitive_load() -> dict[str, bool]:
    """Report whether OAK planner and option manager are actually loaded.

    Both symbols must import and expose their API. Import failure is a real
    down state (fail-closed) — never an unconditional True.
    """
    planner_loaded = False
    option_manager_loaded = False
    try:
        from somabrain.oak.planner import plan_for_tenant

        planner_loaded = callable(plan_for_tenant)
    except Exception:
        planner_loaded = False
    try:
        from somabrain.oak.option_manager import option_manager

        option_manager_loaded = option_manager is not None and callable(
            getattr(option_manager, "list_options", None)
        )
    except Exception:
        option_manager_loaded = False
    return {
        "planner_loaded": planner_loaded,
        "option_manager_loaded": option_manager_loaded,
    }


def milvus_metrics_for_tenant(tenant_id: str) -> dict[str, float | None]:
    """Return Milvus telemetry (p95 latencies + segment load) for a tenant."""

    def _read(gauge, **labels) -> float | None:
        """Execute read.

        Args:
            gauge: The gauge.
        """

        try:
            child = gauge.labels(**labels)
            stored = getattr(child, "_value", None)
            if stored is None:
                return None
            return float(stored.get())
        except Exception:
            return None

    return {
        "search_latency_p95_seconds": _read(
            M.MILVUS_SEARCH_LAT_P95, tenant_id=tenant_id
        ),
        "ingest_latency_p95_seconds": _read(
            M.MILVUS_INGEST_LAT_P95, tenant_id=tenant_id
        ),
        "segment_load": _read(
            M.MILVUS_SEGMENT_LOAD,
            collection=getattr(settings, "SOMABRAIN_MILVUS_COLLECTION"),
        ),
    }
