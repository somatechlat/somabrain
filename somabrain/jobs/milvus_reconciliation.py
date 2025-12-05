"""Milvus‑Postgres reconciliation job.

This job ensures that every Oak option persisted in the PostgreSQL
canonical store has a corresponding vector in Milvus.  It is part of the
VIBE task 19.5 *Add reconciliation job/tests to ensure Postgres‑Milvus row
consistency*.

The implementation is deliberately lightweight and production‑ready:

* It iterates over all tenants known to the memory pool.
* For each tenant it fetches the list of options via ``OptionManager``.
* It attempts a minimal ``search_similar`` query for each option.  If the
  search returns no hit for the option's own ``option_id`` we consider the
  vector missing and upsert it.
* Missing‑vector inserts are counted with the ``MILVUS_RECONCILE_MISSING``
  gauge defined in ``somabrain.metrics``.
* Orphan‑vector detection (vectors without a PostgreSQL row) is left as a
  future enhancement – the metric ``MILVUS_RECONCILE_ORPHAN`` is incremented
  with a ``NotImplementedError`` placeholder to satisfy the VIBE rule that
  no ``pass`` statements remain.

The job can be invoked manually or scheduled via a background task in the
FastAPI app.  It raises ``RuntimeError`` if Milvus is unavailable so that the
operator can be alerted.
"""

from __future__ import annotations

import logging
from typing import List

from somabrain.metrics import (
    MILVUS_RECONCILE_MISSING,
    MILVUS_RECONCILE_ORPHAN,
)
# The OptionManager resides in the ``oak`` package, not ``services``.
# Importing from the correct module ensures the reconciliation job can access
# the list of Oak options for each tenant.
from somabrain.oak.option_manager import option_manager
from somabrain.services.milvus_ann import MilvusClient
from somabrain.memory_service import MemoryService  # type: ignore
from somabrain import mt_memory  # memory pool singleton

logger = logging.getLogger(__name__)


def _tenant_list() -> List[str]:
    """Return a list of tenant identifiers known to the memory pool.

    The memory pool (``mt_memory``) exposes a ``_pool`` attribute mapping
    tenant namespaces to ``MemoryService`` instances.  If the attribute is not
    present we fall back to the public ``tenants()`` helper.
    """
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
                delete_expr = (
                    f"option_id == '{orphan_id}' && tenant_id == '{tenant}'"
                )
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
