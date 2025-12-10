"""Startup event handlers for SomaBrain application.

This module contains all @app.on_event("startup") handlers extracted from app.py.
These functions are designed to be imported and registered with FastAPI's
startup event system.

Note: These functions do NOT have the @app.on_event decorator - they must be
registered in the main app.py using app.add_event_handler("startup", func).
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from fastapi import FastAPI

# Module-level logger
_logger = logging.getLogger("somabrain.lifecycle.startup")


async def startup_mode_banner(app: "FastAPI") -> None:
    """Log mode, derived flags, and deprecation notices on boot.

    This is informational only and does not mutate existing behavior. It helps
    operators verify that SOMABRAIN_MODE is respected and surfaces any legacy
    envs slated for removal.

    Args:
        app: The FastAPI application instance (for accessing app.state if needed)
    """
    try:
        from common.config.settings import settings as _shared
    except Exception:  # pragma: no cover
        _shared = None

    lg = logging.getLogger("somabrain")
    try:
        mode = getattr(_shared, "mode", "prod") if _shared else "prod"
        mode_norm = getattr(_shared, "mode_normalized", "prod") if _shared else "prod"
        api_auth = (
            bool(getattr(_shared, "mode_api_auth_enabled", True)) if _shared else True
        )
        mem_auth = (
            bool(getattr(_shared, "mode_memory_auth_required", True))
            if _shared
            else True
        )
        opa_closed = True  # Strict: always fail-closed
        log_level = (
            str(getattr(_shared, "mode_log_level", "WARNING")) if _shared else "WARNING"
        )
        bundle = (
            str(getattr(_shared, "mode_opa_policy_bundle", "prod"))
            if _shared
            else "prod"
        )
        lg.warning(
            "SomaBrain startup: mode=%s (norm=%s) api_auth=%s memory_auth=%s "
            "opa_fail_closed=%s log_level=%s opa_bundle=%s",
            mode,
            mode_norm,
            api_auth,
            mem_auth,
            opa_closed,
            log_level,
            bundle,
        )
        if _shared is not None:
            for note in getattr(_shared, "deprecation_notices", []) or []:
                lg.warning("DEPRECATION: %s", note)
    except Exception:
        try:
            lg.debug("Failed to emit startup mode banner", exc_info=True)
        except Exception:
            pass


async def init_constitution(app: "FastAPI") -> None:
    """Load the constitution engine (if present) and publish metrics.

    Args:
        app: The FastAPI application instance for storing constitution_engine
    """
    from somabrain import metrics as M

    try:
        from somabrain.constitution import ConstitutionEngine
    except Exception:
        ConstitutionEngine = None

    app.state.constitution_engine = None
    try:
        M.CONSTITUTION_VERIFIED.set(0.0)
    except Exception:
        pass

    if ConstitutionEngine is None:
        return

    start = time.perf_counter()
    verified = False
    try:
        engine = ConstitutionEngine()
        try:
            engine.load()
            verified = bool(engine.verify_signature())
        except Exception as exc:
            _logger.warning("ConstitutionEngine load failed: %s", exc)
            verified = False
        app.state.constitution_engine = engine
    except Exception:
        app.state.constitution_engine = None
        verified = False

    duration = time.perf_counter() - start
    try:
        M.CONSTITUTION_VERIFIED.set(1.0 if verified else 0.0)
        M.CONSTITUTION_VERIFY_LATENCY.observe(duration)
    except Exception:
        pass


async def enforce_kafka_required() -> None:
    """Fail fast if Kafka broker cannot be reached.

    The coding rules require external services to be mandatory when the
    application is running in production. Previously the service would start
    and merely report ``kafka_ok: false`` in the health endpoint. This event
    performs the same check during startup and raises an exception, causing the
    container to exit with a non-zero status so Docker will restart it.

    Raises:
        RuntimeError: If Kafka broker is unavailable or health check fails
    """
    from common.config.settings import settings
    from somabrain.healthchecks import check_kafka

    try:
        kafka_ok = check_kafka(settings.kafka_bootstrap_servers)
        if not kafka_ok:
            raise RuntimeError(
                "Kafka broker unavailable – aborting startup as required by coding rules"
            )
    except Exception as exc:
        raise RuntimeError(f"Kafka health check failed during startup: {exc}")


async def enforce_opa_postgres_required() -> None:
    """Fail fast if OPA or Postgres are not reachable.

    The ``assert_ready`` helper in ``somabrain.common.infra`` performs the
    actual connectivity checks. We call it with ``require_kafka=False`` because
    Kafka is already enforced by ``enforce_kafka_required``. If any check
    fails, we log a clear error and raise ``RuntimeError`` so the container
    exits, satisfying the coding rule that external services must be mandatory.

    Raises:
        RuntimeError: If OPA or Postgres are not ready
    """
    try:
        from somabrain.common.infra import assert_ready

        # OPA and Postgres are required; Kafka is already handled separately.
        assert_ready(require_kafka=False, require_opa=True, require_postgres=True)
    except Exception as exc:
        logging.getLogger("somabrain").error(
            f"Mandatory backend check failed (OPA/Postgres): {exc}"
        )
        raise RuntimeError(f"OPA or Postgres not ready: {exc}")


async def init_health_watchdog(
    app: "FastAPI",
    health_watchdog_task_holder: dict[str, Any],
    cfg: Any,
) -> None:
    """Initialize health watchdog for per-tenant circuit breakers.

    Args:
        app: The FastAPI application instance
        health_watchdog_task_holder: Dict to store the watchdog task reference
        cfg: Configuration object with memory_health_poll_interval
    """
    from somabrain.routers.health import _health_watchdog_coroutine

    if getattr(cfg, "memory_health_poll_interval", 0) > 0:
        task = asyncio.create_task(_health_watchdog_coroutine())
        health_watchdog_task_holder["task"] = task


async def init_tenant_manager(logger: Optional[logging.Logger] = None) -> None:
    """Initialize centralized tenant management system.

    Args:
        logger: Optional logger instance for status messages
    """
    log = logger or _logger
    try:
        from somabrain.tenant_manager import get_tenant_manager

        await get_tenant_manager()
        log.info("Tenant manager initialized successfully")
    except Exception as e:
        log.error(f"Failed to initialize tenant manager: {e}")
        # Don't fail startup - tenant management can be initialized lazily


async def start_outbox_sync(logger: Optional[logging.Logger] = None) -> None:
    """Launch the background outbox synchronization worker.

    The worker runs forever, polling the ``outbox_events`` table and attempting
    to forward pending rows to the external memory service. It respects the
    ``outbox_sync_interval`` setting (seconds) and emits Prometheus metrics.

    Args:
        logger: Optional logger instance for status messages
    """
    log = logger or _logger
    try:
        from common.config.settings import settings
        from somabrain.config import Config
        from somabrain.services.outbox_sync import outbox_sync_loop

        cfg = Config()
        interval = float(getattr(settings, "outbox_sync_interval", 10.0))
        # fire-and-forget – FastAPI will keep the task alive as long as the app runs.
        asyncio.create_task(outbox_sync_loop(cfg, poll_interval=interval))
        log.info("Outbox sync background task started (interval=%s s)", interval)
    except Exception as exc:  # pragma: no cover – startup failures are logged
        log.error("Failed to start outbox sync task: %s", exc, exc_info=True)


async def start_milvus_reconciliation_task() -> None:
    """Launch the Milvus reconciliation loop (Requirement 11.5).

    This task periodically reconciles data between the local database and
    Milvus vector store to ensure consistency.
    """
    from common.config.settings import settings
    from somabrain.jobs.milvus_reconciliation import reconcile as milvus_reconcile

    interval = float(getattr(settings, "milvus_reconcile_interval", 3600.0))
    if interval <= 0:
        logging.getLogger("somabrain").info(
            "Milvus reconciliation disabled (interval=%s)", interval
        )
        return

    async def _runner() -> None:
        log = logging.getLogger("somabrain")
        while True:
            try:
                await asyncio.to_thread(milvus_reconcile)
            except Exception as exc:
                log.error("Milvus reconciliation run failed: %s", exc)
            await asyncio.sleep(interval)

    asyncio.create_task(_runner())
    logging.getLogger("somabrain").info(
        "Milvus reconciliation task started (interval=%s s)", interval
    )
