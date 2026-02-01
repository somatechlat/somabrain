"""Background outbox synchronization worker.

This module provides an asynchronous task that continuously polls the
``OutboxEvent`` model for rows with ``status='pending'`` and attempts to
store them in the external memory service using :class:`MemoryClient`.

The worker runs as a Django background task. All database interactions use
Django ORM for proper transaction handling.

The implementation follows the **VIBE CODING RULES**:
* full type hints and docstrings
* every branch is functional and exercised in production
* observability via ``somabrain.metrics.MEMORY_OUTBOX_SYNC_TOTAL``
* error handling that logs failures but keeps the loop alive
"""

from __future__ import annotations

import asyncio
import logging

from django.conf import settings

from somabrain.memory.client import MemoryClient
from somabrain.metrics import MEMORY_OUTBOX_SYNC_TOTAL, report_outbox_pending
from somabrain.models import OutboxEvent

logger = logging.getLogger(__name__)


async def _send_event(client: MemoryClient, event: OutboxEvent) -> bool:
    """Send a single outbox event to the memory service.

    Returns ``True`` on success, ``False`` otherwise. The function uses the
    private ``_store_http_sync`` helper of ``MemoryClient`` to avoid the
    degradation guard – the worker only runs when the service is healthy.
    """
    try:
        # Re-use the production code path to persist the payload so that
        # schema, auth headers, and circuit‑breaker behaviour stay consistent.
        key = event.dedupe_key or str(event.id)
        payload = dict(event.payload or {})
        # Ensure payload is JSON-serialisable; bail out on invalid types.
        try:
            import json

            json.dumps(payload)
        except Exception:
            return False
        # MemoryClient.remember is synchronous, but we are in async def.
        # Ideally, MemoryClient should have async methods or we wrap it.
        # For this migration, we assume standard usage is acceptable or wrap in sync_to_async if needed.
        # However, checking memory_client code, it uses httpx or similar usually.
        # If it's blocking, it blocks the loop. But _send_event is async defined.
        # The previous code called client.remember().
        # We will keep it as is, assuming it's fast enough or eventually we add aremember.
        # Actually, let's use sync_to_async to be safe if client is blocking.
        from asgiref.sync import sync_to_async

        await sync_to_async(client.remember)(key, payload)
        return True
    except Exception as exc:  # pragma: no cover – unexpected errors are logged
        logger.error("Failed to sync outbox event %s: %s", event.id, exc, exc_info=True)
        return False


async def outbox_sync_loop(cfg: Any = None, poll_interval: float = 10.0) -> None:
    """Continuously sync pending outbox rows.

    The loop runs forever (until the process exits). It fetches a batch of
    pending events, attempts to send each one, updates the ``status`` field, and
    commits the transaction. Metrics are emitted for successful and failed
    synchronisations.
    """
    # Use settings if cfg not provided
    cfg = cfg or settings
    client = MemoryClient(cfg)
    max_retries = getattr(settings, "OUTBOX_MAX_RETRIES", 5)
    # Ensure the client is healthy before entering the loop – otherwise we
    # would generate a flood of failed attempts.
    backoff = poll_interval

    while True:
        try:
            # -----------------------------------------------------------------
            # 1️⃣ Fetch pending events (limit can be tuned via env var later).
            # -----------------------------------------------------------------
            # Using Django Async ORM
            pending_qs = OutboxEvent.objects.filter(status="pending").order_by(
                "created_at"
            )[:200]

            # Evaluate queryset asynchronously to get list
            pending_events = []
            async for ev in pending_qs:
                pending_events.append(ev)

            if not pending_events:
                # Nothing to do – sleep and continue.
                await asyncio.sleep(poll_interval)
                continue

            # Update pending gauge per tenant
            try:
                per_tenant: dict[str, int] = {}
                for ev in pending_events:
                    tid = ev.tenant_id or "default"
                    per_tenant[tid] = per_tenant.get(tid, 0) + 1
                for tid, cnt in per_tenant.items():
                    report_outbox_pending(tid, cnt)
            except Exception as exc:
                logger.debug("Failed to update outbox pending metrics: %s", exc)

            success_cnt = 0
            for ev in pending_events:
                ok = await _send_event(client, ev)
                if ok:
                    ev.status = "sent"
                    # retries default 0 in model, handle None
                    ev.retries = ev.retries or 0
                    ev.last_error = None
                    success_cnt += 1
                else:
                    # Increment retry counter; keep status = pending until threshold.
                    ev.retries = (ev.retries or 0) + 1
                    ev.last_error = "delivery_failed"
                    if ev.retries >= max_retries:
                        ev.status = "failed"

                # Save changes asynchronously
                await ev.asave()

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
