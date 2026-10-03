"""Milvus‑Postgres reconciliation job.

This job enforces Requirement 11.5 from the memory‑client alignment spec:
it detects option vectors missing from Milvus as well as Milvus entries that
no longer have a canonical PostgreSQL row, repairing both without relying on
any mocks or placeholders.

High‑level workflow:

* Enumerate tenants from the live ``mt_memory`` pool.
* For each tenant, pull the canonical option set via ``option_manager``.
* Ensure every option has a Milvus vector; insert if missing and increment
  ``MILVUS_RECONCILE_MISSING``.
* Delete any Milvus vectors whose ``option_id`` is absent from Postgres and
  increment ``MILVUS_RECONCILE_ORPHAN``.

The job may be invoked manually or from the management command.  It raises
``RuntimeError`` when Milvus is unavailable so operators can alert on the
failure.
"""

from __future__ import annotations

import logging

from somabrain.memory.milvus_client import MilvusClient
from somabrain.metrics import (
    MILVUS_RECONCILE_MISSING,
    MILVUS_RECONCILE_ORPHAN,
)
from somabrain.oak.option_manager import option_manager

logger = logging.getLogger(__name__)


def _memory_pool():
    """The live memory pool.

    ``somabrain.runtime`` owns the ``mt_memory`` singleton; ``get_memory_pool``
    returns it and initializes it on first access. This used to walk a chain of
    module lookups — ``runtime``, then the deleted ``somabrain.app``, then a
    hand-built pool — with every step swallowed by ``except Exception``. The
    middle step could never fire and the swallows hid real init failures.
    """
    from somabrain.runtime import get_memory_pool

    return get_memory_pool()


def _tenant_list() -> list[str]:
    """Return a list of tenant identifiers known to the memory pool.

    The memory pool (``mt_memory``) exposes a ``_pool`` attribute mapping
    tenant namespaces to ``MemoryService`` instances.  If the attribute is not
    present we fall back to the public ``tenants()`` helper.
    """
    mt_memory = _memory_pool()
    if hasattr(mt_memory, "_pool") and mt_memory._pool:
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
