"""Lifecycle management for SomaBrain application.

This module contains startup and shutdown event handlers extracted from app.py
to reduce monolithic file size and improve maintainability.

The functions in this module are designed to be registered with Django's
ready() or signal handlers in the main application module.
"""

from somabrain.lifecycle.startup import (
    startup_mode_banner,
    init_constitution,
    enforce_kafka_required,
    enforce_opa_postgres_required,
    init_health_watchdog,
    init_tenant_manager,
    start_outbox_sync,
    start_milvus_reconciliation_task,
)
from somabrain.lifecycle.watchdog import (
    start_memory_watchdog,
    stop_memory_watchdog,
    shutdown_tenant_manager,
)

__all__ = [
    # Startup functions
    "startup_mode_banner",
    "init_constitution",
    "enforce_kafka_required",
    "enforce_opa_postgres_required",
    "init_health_watchdog",
    "init_tenant_manager",
    "start_outbox_sync",
    "start_milvus_reconciliation_task",
    # Shutdown functions
    "start_memory_watchdog",
    "stop_memory_watchdog",
    "shutdown_tenant_manager",
]
