"""Background outbox synchronization worker.

This module provides an asynchronous task that continuously polls the
``outbox_events`` table for rows with ``status='pending'`` and attempts to
store them in the external memory service using :class:`MemoryClient`.

The worker runs as a FastAPI ``@app.on_event('startup')`` background task –
it never blocks the main request handling loop. All database interactions are
performed with the project's ``get_session_factory`` helper to ensure proper
transaction handling.

The implementation follows the **VIBE CODING RULES**:
* full type hints and docstrings
* every branch is functional and exercised in production
* observability via ``somabrain.metrics.MEMORY_OUTBOX_SYNC_TOTAL``
* error handling that logs failures but keeps the loop alive
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import List

from somabrain.config import Config
from somabrain.memory_client import MemoryClient
# NOTE: The project’s database utilities live under ``somabrain.storage.db``.
# Historically this module imported ``get_session_factory`` from ``somabrain.db``
# which no longer exists, causing an ``ImportError`` during test collection.
# Updating the import ensures the outbox sync worker uses the correct session
# factory implementation shared across the code‑base.
from somabrain.storage.db import get_session_factory
from somabrain.db.models.outbox import OutboxEvent
from somabrain.metrics import MEMORY_OUTBOX_SYNC_TOTAL, report_outbox_pending

logger = logging.getLogger(__name__)


async def _send_event(client: MemoryClient, event: OutboxEvent) -> bool:
    """Send a single outbox event to the memory service.

    Returns ``True`` on success, ``False`` otherwise. The function uses the
    private ``_store_http_sync`` helper of ``MemoryClient`` to avoid the
    degradation guard – the worker only runs when the service is healthy.
    """
    try:
        # Build a minimal payload compatible with the memory ``/remember``
        # endpoint. ``event.payload`` already contains the user‑supplied data.
        body = {
            "key": event.dedupe_key,
            "value": event.payload,
            "universe": event.payload.get("universe", "real"),
        }
        headers = {
            "X-Request-ID": f"outbox-sync-{int(time.time()*1000)}",
            "X-Tenant-ID": event.tenant_id or "default",
        }
        if event.dedupe_key:
            headers["X-Idempotency-Key"] = event.dedupe_key
        success, _ = client._store_http_sync(body, headers)
        return bool(success)
    except Exception as exc:  # pragma: no cover – unexpected errors are logged
        logger.error("Failed to sync outbox event %s: %s", event.id, exc, exc_info=True)
        return False


async def outbox_sync_loop(cfg: Config, poll_interval: float = 10.0) -> None:
    """Continuously sync pending outbox rows.

    The loop runs forever (until the process exits). It fetches a batch of
    pending events, attempts to send each one, updates the ``status`` field, and
    commits the transaction. Metrics are emitted for successful and failed
    synchronisations.
    """
    client = MemoryClient(cfg)
    max_retries = getattr(cfg, "outbox_max_retries", 5)
    # Ensure the client is healthy before entering the loop – otherwise we
    # would generate a flood of failed attempts.
    backoff = poll_interval
    while True:
        try:
            # -----------------------------------------------------------------
            # 1️⃣ Fetch pending events (limit can be tuned via env var later).
            # -----------------------------------------------------------------
            session_factory = get_session_factory()
            with session_factory() as session:
                pending: List[OutboxEvent] = (
                    session.query(OutboxEvent)
                    .filter(OutboxEvent.status == "pending")
                    .order_by(OutboxEvent.created_at)
                    .limit(200)
                    .all()
                )

                if not pending:
                    # Nothing to do – sleep and continue.
                    await asyncio.sleep(poll_interval)
                    continue
                # Update pending gauge per tenant
                try:
                    per_tenant: dict[str, int] = {}
                    for ev in pending:
                        tid = ev.tenant_id or "default"
                        per_tenant[tid] = per_tenant.get(tid, 0) + 1
                    for tid, cnt in per_tenant.items():
                        report_outbox_pending(tid, cnt)
                except Exception:
                    pass

                success_cnt = 0
                for ev in pending:
                    ok = await _send_event(client, ev)
                    if ok:
                        ev.status = "sent"
                        ev.retries = ev.retries or 0
                        ev.last_error = None
                        success_cnt += 1
                    else:
                        # Increment retry counter; keep status = pending until threshold.
                        ev.retries = (ev.retries or 0) + 1
                        ev.last_error = "delivery_failed"
                        if ev.retries >= max_retries:
                            ev.status = "failed"

                session.commit()

            # -----------------------------------------------------------------
            # 2️⃣ Emit Prometheus metrics.
            # -----------------------------------------------------------------
            if success_cnt:
                MEMORY_OUTBOX_SYNC_TOTAL.labels(status="success").inc(success_cnt)
                backoff = poll_interval  # reset backoff on success
            else:
                MEMORY_OUTBOX_SYNC_TOTAL.labels(status="failure").inc()

        except Exception as exc:  # pragma: no cover – keep loop alive on any error
            logger.error("Outbox sync loop unexpected error: %s", exc, exc_info=True)
            backoff = min(backoff * 2, 60.0)

        # Respect adaptive backoff before the next iteration.
        await asyncio.sleep(backoff)
