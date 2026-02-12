"""Watchdog and shutdown event handlers for SomaBrain application.

This module contains memory watchdog functions and shutdown handlers
extracted from app.py.

Note: These functions do NOT have the @app.on_event decorator - they must be
registered in the main app.py using app.add_event_handler().
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional

# Module-level logger
_logger = logging.getLogger("somabrain.lifecycle.watchdog")


async def start_memory_watchdog(
    app: Any,
    memory_service: Any,
) -> None:
    """Start the memory service watchdog loop.

    The watchdog periodically attempts to reset the circuit breaker if needed,
    ensuring the memory service can recover from transient failures.

    Args:
        app: The Django Ninja application instance for storing the watchdog task
        memory_service: The MemoryService instance to monitor
    """

    async def _watchdog_loop() -> None:
        """Execute watchdog loop."""

        while True:
            try:
                # Attempt circuit reset periodically; updates circuit breaker metric internally
                memory_service._reset_circuit_if_needed()
            except Exception:
                pass
            await asyncio.sleep(5.0)

    try:
        task = asyncio.create_task(_watchdog_loop())
        app.state._memory_watchdog = task
    except Exception:
        # best-effort; don't fail startup on watchdog init
        pass


async def stop_memory_watchdog(app: Any) -> None:
    """Stop the memory service watchdog loop.

    Args:
        app: The Django Ninja application instance containing the watchdog task
    """
    try:
        task = getattr(app.state, "_memory_watchdog", None)
        if task is not None:
            task.cancel()
    except Exception:
        pass


async def shutdown_tenant_manager(logger: Optional[logging.Logger] = None) -> None:
    """Shutdown tenant manager gracefully.

    Skipped in Standalone mode (somabrain.aaas not in INSTALLED_APPS).

    Args:
        logger: Optional logger instance for status messages
    """
    log = logger or _logger
    try:
        from django.apps import apps

        if not apps.is_installed("somabrain.aaas"):
            log.info("Standalone mode — tenant manager shutdown skipped")
            return

        from somabrain.aaas.logic.tenant_manager import close_tenant_manager

        await close_tenant_manager()
        log.info("Tenant manager shutdown completed")
    except Exception as e:
        log.error(f"Error shutting down tenant manager: {e}")
