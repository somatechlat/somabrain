"""Health Watchdog - Background health monitoring for circuit breakers.

Migrated from somabrain/routers/health_watchdog.py.
Provides background health monitoring for per-tenant circuit breakers.

Thread Safety:
    The watchdog runs as an asyncio task and uses thread-safe access patterns
    for shared state.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from django.conf import settings

logger = logging.getLogger("somabrain.health.watchdog")

_LOG_PREFIX = "[HEALTH]"
_LOG_TENANT_FMT = "tenant=%s"

_health_watchdog_task: Optional[asyncio.Task] = None


def _get_runtime():
    """Lazy import of runtime module to access singletons."""
    import importlib.util
    import os
    import sys

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


def _get_mt_memory():
    """Get the multi-tenant memory singleton."""
    rt = _get_runtime()
    if rt:
        return getattr(rt, "mt_memory", None)
    return None


async def _health_watchdog_coroutine():
    """Periodic health checks for per-tenant circuit breakers."""
    from somabrain.services.memory_service import MemoryService

    mt_memory = _get_mt_memory()
    poll_interval = float(getattr(settings, "MEMORY_HEALTH_POLL_INTERVAL", 5.0))

    while True:
        try:
            # Get all active tenants from memory pool
            tenants = []
            if mt_memory:
                if hasattr(mt_memory, "_pool") and mt_memory._pool:
                    tenants = list(mt_memory._pool.keys())
                elif hasattr(mt_memory, "tenants"):
                    tenants = mt_memory.tenants() or []

            for tenant_namespace in tenants:
                try:
                    memsvc = MemoryService(mt_memory, tenant_namespace)
                    circuit_state = memsvc.get_circuit_state()

                    if circuit_state["circuit_open"]:
                        health_result = memsvc.health()
                        healthy = False

                        if isinstance(health_result, dict):
                            healthy = health_result.get("healthy", False)
                            if not healthy:
                                comps = health_result.get("components", {})
                                mem = comps.get("memory", {})
                                healthy = mem.get("healthy", False)
                            if not healthy:
                                healthy = health_result.get(
                                    "http", False
                                ) or health_result.get("ok", False)

                        if healthy:
                            MemoryService.reset_circuit_for_tenant(memsvc.tenant_id)
                            logger.info(
                                "%s Circuit breaker RESET | %s | action=reset",
                                _LOG_PREFIX,
                                _LOG_TENANT_FMT,
                                memsvc.tenant_id,
                            )

                except Exception as e:
                    logger.error(
                        "%s Health check FAILED | %s | error=%s",
                        _LOG_PREFIX,
                        _LOG_TENANT_FMT,
                        tenant_namespace,
                        str(e),
                    )

        except Exception as e:
            logger.error(
                "%s Watchdog ERROR | error=%s",
                _LOG_PREFIX,
                str(e),
            )

        await asyncio.sleep(poll_interval)


def start_health_watchdog() -> Optional[asyncio.Task]:
    """Start the health watchdog background task."""
    global _health_watchdog_task
    if _health_watchdog_task is None:
        _health_watchdog_task = asyncio.create_task(_health_watchdog_coroutine())
    return _health_watchdog_task


def stop_health_watchdog() -> None:
    """Stop the health watchdog background task."""
    global _health_watchdog_task
    if _health_watchdog_task is not None:
        _health_watchdog_task.cancel()
        _health_watchdog_task = None