"""Sleep Router - Sleep cycle management endpoints.

Extracted from somabrain/app.py per global-architecture-refactor spec.
Provides /sleep/run, /sleep/status, /sleep/status/all endpoints.
"""

from __future__ import annotations

import logging
import threading as _thr
import time
from typing import Any, Dict

from fastapi import APIRouter, Request

from common.config.settings import settings
from somabrain import consolidation as CONS, schemas as S
from somabrain.auth import require_admin_auth, require_auth
from somabrain.tenant import get_tenant as get_tenant_async

# ---------------------------------------------------------------------------
# Logging Configuration
# ---------------------------------------------------------------------------
logger = logging.getLogger("somabrain.routers.sleep")

router = APIRouter(tags=["sleep"])


# ---------------------------------------------------------------------------
# Module-level state for sleep tracking
# ---------------------------------------------------------------------------
_sleep_last: Dict[str, Dict[str, float]] = {}
_sleep_stop = _thr.Event()
_sleep_thread: _thr.Thread | None = None


# ---------------------------------------------------------------------------
# Lazy accessors for app-level singletons to avoid circular imports
# ---------------------------------------------------------------------------


def _get_runtime():
    """Lazy import of runtime module to access singletons."""
    import importlib.util
    import os
    import sys

    _runtime_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "runtime.py")
    _spec = importlib.util.spec_from_file_location("somabrain.runtime_module", _runtime_path)
    if _spec and _spec.name in sys.modules:
        return sys.modules[_spec.name]
    # Fallback: search loaded modules
    for m in list(sys.modules.values()):
        try:
            mf = getattr(m, "__file__", "") or ""
            if mf.endswith(os.path.join("somabrain", "runtime.py")):
                return m
        except Exception:
            continue
    return None


def _get_app_config():
    """Get the application configuration."""
    return settings


def _get_mt_wm():
    """Get the multi-tenant working memory singleton."""
    rt = _get_runtime()
    if rt:
        return getattr(rt, "mt_wm", None)
    return None


def _get_mt_memory():
    """Get the multi-tenant memory singleton."""
    rt = _get_runtime()
    if rt:
        return getattr(rt, "mt_memory", None)
    return None


# ---------------------------------------------------------------------------
# Sleep state accessors (for external access)
# ---------------------------------------------------------------------------


def get_sleep_last() -> Dict[str, Dict[str, float]]:
    """Get the sleep tracking state dictionary."""
    return _sleep_last


def set_sleep_last(tenant_id: str, phase: str, timestamp: float) -> None:
    """Update sleep tracking state for a tenant."""
    _sleep_last.setdefault(tenant_id, {})[phase] = timestamp


# ---------------------------------------------------------------------------
# Background sleep loop
# ---------------------------------------------------------------------------


def _sleep_loop() -> None:
    """Background thread that runs NREM/REM consolidation cycles."""
    cfg = _get_app_config()
    mt_wm = _get_mt_wm()
    mt_memory = _get_mt_memory()

    interval = max(0, int(getattr(cfg, "sleep_interval_seconds", 0)))
    if interval <= 0:
        return

    while not _sleep_stop.is_set():
        try:
            tenants = mt_wm.tenants() if mt_wm else ["public"]
            tenants = tenants or ["public"]

            for tid in tenants:
                CONS.run_nrem(
                    tid,
                    cfg,
                    mt_wm,
                    mt_memory,
                    top_k=cfg.nrem_batch_size,
                    max_summaries=cfg.max_summaries_per_cycle,
                )
                set_sleep_last(tid, "nrem", time.time())

                CONS.run_rem(
                    tid,
                    cfg,
                    mt_wm,
                    mt_memory,
                    recomb_rate=cfg.rem_recomb_rate,
                    max_summaries=cfg.max_summaries_per_cycle,
                )
                set_sleep_last(tid, "rem", time.time())
        except Exception:
            logger.debug("Sleep loop iteration failed", exc_info=True)

        _sleep_stop.wait(interval)


def start_sleep_thread() -> None:
    """Start the background sleep consolidation thread."""
    global _sleep_thread
    if _sleep_thread is None or not _sleep_thread.is_alive():
        _sleep_stop.clear()
        _sleep_thread = _thr.Thread(target=_sleep_loop, daemon=True)
        _sleep_thread.start()
        logger.info("Sleep consolidation thread started")


def stop_sleep_thread() -> None:
    """Stop the background sleep consolidation thread."""
    global _sleep_thread
    _sleep_stop.set()
    if _sleep_thread is not None:
        _sleep_thread.join(timeout=5.0)
        _sleep_thread = None
        logger.info("Sleep consolidation thread stopped")


# ---------------------------------------------------------------------------
# Sleep Endpoints
# ---------------------------------------------------------------------------


@router.post("/sleep/run", response_model=S.SleepRunResponse)
async def sleep_run(body: S.SleepRunRequest, request: Request) -> S.SleepRunResponse:
    """Trigger manual NREM/REM consolidation cycle for the current tenant."""
    cfg = _get_app_config()
    mt_wm = _get_mt_wm()
    mt_memory = _get_mt_memory()

    require_auth(request, cfg)
    ctx = await get_tenant_async(request, cfg.namespace)

    # Body is a Pydantic model; use attributes with defaults
    do_nrem = getattr(body, "nrem", True) if hasattr(body, "nrem") else True
    do_rem = getattr(body, "rem", True) if hasattr(body, "rem") else True

    details: Dict[str, Any] = {}

    if do_nrem:
        details["nrem"] = CONS.run_nrem(
            ctx.tenant_id,
            cfg,
            mt_wm,
            mt_memory,
            top_k=cfg.nrem_batch_size,
            max_summaries=cfg.max_summaries_per_cycle,
        )
        set_sleep_last(ctx.tenant_id, "nrem", time.time())

    if do_rem:
        details["rem"] = CONS.run_rem(
            ctx.tenant_id,
            cfg,
            mt_wm,
            mt_memory,
            recomb_rate=cfg.rem_recomb_rate,
            max_summaries=cfg.max_summaries_per_cycle,
        )
        set_sleep_last(ctx.tenant_id, "rem", time.time())

    run_id = f"sleep_{ctx.tenant_id}_{int(time.time() * 1000)}"

    return S.SleepRunResponse(
        ok=True,
        run_id=run_id,
        started_at_ms=int(time.time() * 1000),
        mode=(
            "nrem/rem"
            if do_nrem and do_rem
            else ("nrem" if do_nrem else ("rem" if do_rem else "none"))
        ),
        details=details,
    )


@router.get("/sleep/status", response_model=S.SleepStatusResponse)
async def sleep_status(request: Request) -> S.SleepStatusResponse:
    """Get sleep consolidation status for the current tenant."""
    cfg = _get_app_config()

    require_auth(request, cfg)
    ctx = await get_tenant_async(request, cfg.namespace)

    ten = ctx.tenant_id
    last = _sleep_last.get(ten, {})

    return {
        "enabled": bool(cfg.consolidation_enabled),
        "interval_seconds": int(getattr(cfg, "sleep_interval_seconds", 0) or 0),
        "last": {"nrem": last.get("nrem"), "rem": last.get("rem")},
    }


@router.get("/sleep/status/all", response_model=S.SleepStatusAllResponse)
async def sleep_status_all(request: Request) -> S.SleepStatusAllResponse:
    """Admin view: list sleep status for all known tenants.

    Returns { enabled, interval_seconds, tenants: { <tid>: {nrem, rem} } }
    """
    cfg = _get_app_config()
    mt_wm = _get_mt_wm()

    ctx = await get_tenant_async(request, cfg.namespace)
    require_admin_auth(request, cfg)

    try:
        tenants = mt_wm.tenants() if mt_wm else [ctx.tenant_id or "public"]
        tenants = tenants or [ctx.tenant_id or "public"]
    except Exception:
        tenants = [ctx.tenant_id or "public"]

    out: Dict[str, Dict[str, float | None]] = {}
    for tid in tenants:
        last = _sleep_last.get(tid, {})
        out[tid] = {"nrem": last.get("nrem"), "rem": last.get("rem")}

    return {
        "enabled": bool(cfg.consolidation_enabled),
        "interval_seconds": int(getattr(cfg, "sleep_interval_seconds", 0) or 0),
        "tenants": out,
    }
