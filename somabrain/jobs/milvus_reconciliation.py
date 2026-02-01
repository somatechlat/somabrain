"""Milvus‑Postgres reconciliation job.

This job enforces Requirement 11.5 from the memory‑client alignment spec:
it detects option vectors missing from Milvus as well as Milvus entries that
no longer have a canonical PostgreSQL row, repairing both without relying on
any mocks or placeholders.

High‑level workflow:

* Enumerate tenants from the live ``mt_memory`` pool (falling back to the
  runtime/app modules if needed).
* For each tenant, pull the canonical option set via ``option_manager``.
* Ensure every option has a Milvus vector; insert if missing and increment
  ``MILVUS_RECONCILE_MISSING``.
* Delete any Milvus vectors whose ``option_id`` is absent from Postgres and
  increment ``MILVUS_RECONCILE_ORPHAN``.

The job may be invoked manually or via a background scheduler (see
``somabrain.app``).  It raises ``RuntimeError`` when Milvus is unavailable so
operators can alert on the failure.
"""

from __future__ import annotations

import logging
from typing import List

from somabrain.metrics import (
    MILVUS_RECONCILE_MISSING,
    MILVUS_RECONCILE_ORPHAN,
)
from somabrain.apps.memory.milvus_client import MilvusClient
from somabrain.oak.option_manager import option_manager

logger = logging.getLogger(__name__)


def _memory_pool():
    """Return the global memory pool instance, regardless of import order.

    Attempts to retrieve the mt_memory pool from the runtime module first,
    then falls back to the app module. If neither has an initialized pool,
    creates a new MultiTenantMemory instance using centralized Settings
    and caches it on the runtime module for subsequent calls.

    Returns:
        MultiTenantMemory: The global memory pool instance for tenant-scoped
                          memory operations.

    Notes:
        - Import order agnostic: handles circular import scenarios gracefully
        - Lazy initialization: creates pool only when first accessed
        - Caches result on runtime module to avoid repeated instantiation
        - Uses centralized Settings for pool configuration
    """

    # Type ignores: These imports are intentionally dynamic to handle circular import
    # scenarios and runtime module availability. The modules may not exist at static
    # analysis time but are available at runtime after app initialization.
    runtime_mod = None
    try:
        from somabrain import runtime as _rt  # type: ignore[import-not-found]

        runtime_mod = _rt
        pool = getattr(_rt, "mt_memory", None)
    except Exception:
        pool = None
    if pool is None:
        try:
            import somabrain.app as _app_mod  # type: ignore[import-not-found]

            pool = getattr(_app_mod, "mt_memory", None)
        except Exception:
            pool = None
    if pool is None:
        from django.conf import settings as cfg

        from somabrain.apps.memory.pool import MultiTenantMemory

        pool = MultiTenantMemory(cfg)
        if runtime_mod is not None:
            try:
                setattr(runtime_mod, "mt_memory", pool)
            except Exception as exc:
                logger.debug("Failed to cache mt_memory on runtime module: %s", exc)
    return pool


def _tenant_list() -> List[str]:
    """Return a list of tenant identifiers known to the memory pool.

    The memory pool (``mt_memory``) exposes a ``_pool`` attribute mapping
    tenant namespaces to ``MemoryService`` instances.  If the attribute is not
    present we fall back to the public ``tenants()`` helper.
    """
    mt_memory = _memory_pool()
    if hasattr(mt_memory, "_pool") and getattr(mt_memory, "_pool"):
        return list(mt_memory._pool.keys())
    if hasattr(mt_memory, "tenants"):
        return mt_memory.tenants() or []
    return []


def reconcile() -> None:
    """Synchronise PostgreSQL‑stored options with Milvus vectors.

    The function is idempotent – running it repeatedly will not create
    duplicate vectors because Milvus ``upsert_option`` overwrites existing rows.
    """
    milvus = MilvusClient()
    if milvus.collection is None:
        raise RuntimeError("Milvus collection unavailable – cannot run reconciliation")

    for tenant in _tenant_list():
        logger.info("Reconciling Milvus vectors for tenant %s", tenant)
        # Fetch all options for the tenant.
        options = option_manager.list_options(tenant)
        for opt in options:
            # Perform a narrow search for the option_id.
            try:
                hits = milvus.search_similar(
                    tenant_id=tenant,
                    payload=opt.payload,
                    top_k=1,
                    similarity_threshold=0.0,  # retrieve any match
                )
                # If the option_id is not among the hits, the vector is missing.
                if not any(hit_id == opt.option_id for hit_id, _ in hits):
                    milvus.upsert_option(tenant, opt.option_id, opt.payload)
                    MILVUS_RECONCILE_MISSING.labels(tenant_id=tenant).inc()
                    logger.debug(
                        "Inserted missing Milvus vector for option %s (tenant %s)",
                        opt.option_id,
                        tenant,
                    )
            except Exception as exc:
                logger.error(
                    "Failed to reconcile option %s for tenant %s: %s",
                    opt.option_id,
                    tenant,
                    exc,
                )

        # -----------------------------------------------------------------
        # Orphan detection – remove Milvus vectors that have no corresponding
        # PostgreSQL option. This fulfills VIBE task 19.5 (no orphans).
        # -----------------------------------------------------------------
        try:
            # Retrieve all option IDs stored in Milvus for this tenant.
            # ``query`` returns a list of dictionaries with the requested fields.
            milvus_option_records = milvus.collection.query(
                expr=f"tenant_id == '{tenant}'",
                output_fields=["option_id"],
            )
            milvus_option_ids = {rec["option_id"] for rec in milvus_option_records}
            postgres_option_ids = {opt.option_id for opt in options}

            orphan_ids = milvus_option_ids - postgres_option_ids
            for orphan_id in orphan_ids:
                # Delete each orphan vector individually.
                delete_expr = f"option_id == '{orphan_id}' && tenant_id == '{tenant}'"
                milvus.collection.delete(expr=delete_expr)
                MILVUS_RECONCILE_ORPHAN.labels(tenant_id=tenant).inc()
                logger.info(
                    "Removed orphan Milvus vector %s for tenant %s", orphan_id, tenant
                )
        except Exception as exc:
            # Any failure in orphan detection should be logged but must not
            # abort the entire reconciliation run.
            logger.error(
                "Failed to reconcile orphan vectors for tenant %s: %s", tenant, exc
            )
