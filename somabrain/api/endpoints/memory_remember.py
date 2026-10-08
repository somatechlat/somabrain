"""Remember Endpoints - Django Ninja Version

Migrated from FastAPI to Django Ninja.
Complex memory write logic (batch, signals, embedding).
"""

from __future__ import annotations

from somabrain.embed_dim import ensure_embedding_dim

import asyncio
import logging
import uuid

import httpx
import numpy as np
from asgiref.sync import sync_to_async
from django.conf import settings
from django.http import HttpRequest
from ninja import Router
from ninja.errors import HttpError

from somabrain.api.auth import api_key_auth, bind_credential_tenant, require_auth
from somabrain.api.memory.helpers import (
    _compose_memory_payload,
    _get_embedder,
    _get_memory_pool,
    _get_wm,
    _resolve_namespace,
    _serialize_coord,
)
from somabrain.api.memory.models import (
    MemoryBatchWriteRequest,
    MemoryBatchWriteResponse,
    MemoryDurability,
    MemorySignalFeedback,
    MemoryWriteRequest,
    MemoryWriteResponse,
)
from somabrain.core.exceptions import CircuitBreakerOpen, MemoryServiceError
from somabrain.metrics import record_memory_snapshot
from somabrain.services.memory_service import MemoryService

logger = logging.getLogger("somabrain.api.endpoints.memory_remember")

# Per-tenant background LTM persist failures (fast NEXT-call signal; durable truth is the outbox row).
_background_ltm_failures: dict[str, int] = {}

# Strong refs to in-flight background tasks — asyncio only keeps weak refs.
_background_tasks: set[asyncio.Task] = set()


async def _durable_accept(
    *,
    tenant: str,
    key: str,
    stored_payload: dict,
    request_id: str,
    coord: tuple | None,
) -> int:
    """T-6 durable accept: outbox row written and verified before any hop.

    Idempotency is coord-only (INVARIANTS §3.3) — never a request id, never a
    UUID. Same (tenant, coord) collapses to one row. Refuses if row is missing.
    """
    from django.db import IntegrityError

    from somabrain.admin.core.models import OutboxEvent
    from somabrain.db.outbox import (
        _idempotency_key,
        enqueue_memory_event,
        get_event_by_dedupe_key,
    )

    try:
        event_id = await sync_to_async(enqueue_memory_event)(
            topic="memory.store",
            payload={"key": key, "payload": stored_payload, "request_id": request_id},
            tenant_id=tenant,
            coord=coord,
            extra_key=None,
            check_backpressure_flag=True,
        )
    except IntegrityError:
        # Same (tenant, coord) already accepted — replay, not a new memory.
        existing = await sync_to_async(get_event_by_dedupe_key)(
            _idempotency_key("memory.store", coord, tenant, None), tenant_id=tenant
        )
        if existing is None:
            raise
        return int(existing.id)
    row = await sync_to_async(
        lambda: OutboxEvent.objects.filter(id=event_id)
        .values("id", "status", "tenant_id", "topic")
        .first()
    )()
    if row is None:
        raise HttpError(
            503,
            f"durable accept failed: outbox row id={event_id} missing after enqueue",
        )
    return event_id


async def _replay_pending_to_store(memsvc: MemoryService, tenant_id: str) -> int:
    """Drain still-pending memory.store rows to the STORE, then mark sent.

    T-6: only a store ack closes an event. Kafka publish is not a store ack.
    Idempotent — coord-only dedupe collapses retries of a landed coord.
    """
    from somabrain.admin.core.models import OutboxEvent
    from somabrain.db.outbox import mark_event_sent

    def _fetch_pending():
        return list(
            OutboxEvent.objects.filter(
                topic="memory.store", tenant_id=tenant_id, status="pending"
            )
            .order_by("created_at")
            .values("id", "payload")
        )

    rows = await sync_to_async(_fetch_pending)()
    closed = 0
    for row in rows:
        payload = dict(row.get("payload") or {})
        key = payload.get("key")
        if key is None:
            continue
        try:
            await memsvc.aremember(key, payload.get("payload") or payload)
        except Exception as exc:
            _note_background_ltm_failure(tenant_id, str(key), row["id"], exc)
            continue
        await sync_to_async(mark_event_sent)(row["id"])
        closed += 1
    return closed


def _note_background_ltm_failure(tenant_id: str, key: str, event_id: int, exc: Exception) -> None:
    """Record a background LTM persist failure for the NEXT response.

    Leaves the outbox row pending (T-6). Error log + metric — never a lone warning.
    """
    _background_ltm_failures[tenant_id] = _background_ltm_failures.get(tenant_id, 0) + 1
    logger.error(
        "Background LTM persist failed; outbox row stays pending for replay. "
        "tenant=%s key=%s event_id=%s: %s",
        tenant_id,
        key,
        event_id,
        exc,
        exc_info=exc,
    )
    try:
        from somabrain.metrics import MEMORY_OUTBOX_SYNC_TOTAL, report_outbox_pending
        from somabrain.db.outbox import get_pending_count

        MEMORY_OUTBOX_SYNC_TOTAL.labels(status="failure").inc()
        report_outbox_pending(tenant_id, get_pending_count(tenant_id))
    except Exception:
        logger.exception(
            "Failed to report background LTM persist failure metric for tenant=%s",
            tenant_id,
        )


async def _persist_ltm_in_background(
    memsvc: MemoryService,
    key: str,
    stored_payload: dict,
    request_id: str,
    event_id: int,
    tenant_id: str,
) -> None:
    """LTM persist after the 200 (fast-ack). Store ack marks sent; failure
    leaves the row pending and surfaces (T-6). ``event_id`` is the OutboxEvent PK.
    """
    try:
        await memsvc.aremember(key, stored_payload)
    except Exception as exc:
        _note_background_ltm_failure(tenant_id, key, event_id, exc)
        return
    from somabrain.db.outbox import mark_event_sent

    try:
        await sync_to_async(mark_event_sent)(event_id)
    except Exception:
        logger.exception(
            "Failed to mark outbox event id=%s sent for tenant=%s key=%s",
            event_id,
            tenant_id,
            key,
        )
        raise
    try:
        from somabrain.metrics import MEMORY_OUTBOX_SYNC_TOTAL

        MEMORY_OUTBOX_SYNC_TOTAL.labels(status="success").inc()
    except Exception:
        logger.exception(
            "Failed to report background LTM persist success metric for tenant=%s",
            tenant_id,
        )


router = Router(tags=["memory"])


def _map_memory_error(exc: Exception) -> HttpError:
    """Map a memory backend exception to an HTTP error response."""
    if isinstance(exc, httpx.TimeoutException):
        return HttpError(504, "memory backend timeout")
    if isinstance(exc, httpx.ConnectError):
        return HttpError(503, "memory backend unreachable")
    if isinstance(exc, httpx.HTTPStatusError):
        return HttpError(502, f"memory backend error: {exc.response.status_code}")
    if isinstance(exc, CircuitBreakerOpen):
        return HttpError(503, str(exc))
    if isinstance(exc, MemoryServiceError):
        return HttpError(502, str(exc))
    if isinstance(exc, RuntimeError):
        return HttpError(503, str(exc))
    from somabrain.db.outbox import OutboxBackpressureError

    if isinstance(exc, OutboxBackpressureError):
        # The outbox is the durable accept. Refuse the write rather than
        # pretend — Rule 2 (no fallback) and T-6 together.
        return HttpError(503, str(exc))
    return HttpError(500, f"unexpected memory error: {exc}")


def _ensure_runtime():
    """Ensure config runtime is accessible."""

    # In sync code we might just rely on side-effects or call async if valid
    # For now, assuming runtime is initialized by WSGI/ASGI entrypoint or middleware


# Splitting logic to handle async nature properly
# We need to redefine the view as async because memsvc likely uses async HTTP/DB
@router.post("/remember", response=MemoryWriteResponse, auth=api_key_auth)
async def remember_memory_async(request: HttpRequest, payload: MemoryWriteRequest):
    """Store a memory (Async)."""
    require_auth(request, settings)
    pool = _get_memory_pool()
    wm = _get_wm()
    embedder = _get_embedder()

    if not pool:
        raise HttpError(503, "Memory services not available")

    # Tenant scoping: credential tenant is the sole authority. Body tenant_id /
    # tenant and the X-Tenant-ID header are assertions only — a mismatch is 403
    # (thread.py contract). Never silently default.
    asserted = (
        payload.tenant
        or payload.tenant_id
        or request.headers.get("X-Tenant-ID")
        or None
    )
    tenant = bind_credential_tenant(request, asserted)
    payload.tenant = tenant
    payload.tenant_id = tenant

    resolved_ns = _resolve_namespace(tenant, payload.namespace)
    memsvc = MemoryService(pool, resolved_ns)
    memsvc._reset_circuit_if_needed()

    actor = request.headers.get("X-Actor") or "memory-api"
    stored_payload, signal_data, seed_text = _compose_memory_payload(
        tenant=payload.tenant,
        namespace=payload.namespace,
        key=payload.key,
        value=payload.value,
        meta=payload.meta,
        universe=payload.universe,
        attachments=payload.attachments,
        links=payload.links,
        tags=payload.tags,
        policy_tags=payload.policy_tags,
        signals=payload.signals,
        importance=payload.importance,
        novelty=payload.novelty,
        ttl_seconds=payload.ttl_seconds,
        trace_id=payload.trace_id,
        actor=actor,
        text=payload.text,
        kind=payload.kind,
        session_id=payload.session_id,
        salience=payload.salience,
        source=payload.source,
        coord=payload.coord,
        embedding=ensure_embedding_dim(payload.embedding),
    )

    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    persisted_to_ltm = False
    coord = None
    degraded_warnings: list[str] = []
    # T-6 durability state. Defaults to the weakest claim; each path below
    # promotes it only when it has evidence for that promotion.
    durability: MemoryDurability = MemoryDurability.DEGRADED_JOURNAL
    outbox_event_id: int | None = None
    queued_for_ltm = False

    fast_ack = request.headers.get("X-Soma-Fast-Ack", "").lower() == "true" or bool(
        getattr(settings, "SOMABRAIN_MEMORY_FAST_ACK")
    )

    # T-6: durable accept BEFORE the store hop on every path. No 200 without
    # the store ack or a verified outbox row.
    try:
        coord = memsvc.client().coord_for_key(payload.key, payload.universe)
    except Exception as exc:
        raise _map_memory_error(exc) from exc

    try:
        outbox_event_id = await _durable_accept(
            tenant=payload.tenant,
            key=payload.key,
            stored_payload=stored_payload,
            request_id=request_id,
            coord=coord,
        )
    except HttpError:
        raise
    except Exception as exc:
        # NO FALLBACK — refuse if the durable accept cannot be written.
        logger.error("Durable accept failed: %s", exc, exc_info=exc)
        raise _map_memory_error(exc) from exc

    queued_for_ltm = True
    durability = MemoryDurability.DURABLE_OUTBOX

    if memsvc._is_circuit_open():
        # Store is down. The outbox row IS the durable accept; leave it
        # pending for replay. Never fall through to a journal-only 200.
        degraded_warnings.append("memory-backend-unavailable:queued-for-replay")
        degraded_warnings.append("ltm-persist:queued-async")
    elif fast_ack:
        # Fast-ack: bounded latency. LTM persist runs in the background; the
        # outbox row is already verified. Hold a strong ref — asyncio only
        # keeps weak refs to tasks (C1-7).
        task = asyncio.create_task(
            _persist_ltm_in_background(
                memsvc,
                payload.key,
                stored_payload,
                request_id,
                outbox_event_id,
                payload.tenant,
            )
        )
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)
        degraded_warnings.append("ltm-persist:queued-async")
    else:
        # Sync path: outbox row already written (above). Now the store hop.
        try:
            coord = await memsvc.aremember(payload.key, stored_payload)
            persisted_to_ltm = True
            durability = MemoryDurability.PERSISTED_LTM
            queued_for_ltm = False
            from somabrain.db.outbox import mark_event_sent

            await sync_to_async(mark_event_sent)(outbox_event_id)
            # APM-1: durable store is a memory-learning event
            from somabrain.learning.memory_events import remember_learned

            remember_learned(payload.tenant, kind="store_admit")
        except CircuitBreakerOpen as exc:
            # Outbox row stays pending — durable and replayable.
            degraded_warnings.append(
                f"memory-backend-unavailable:queued-for-replay:{exc}"
            )
            degraded_warnings.append("ltm-persist:queued-async")
        except (httpx.HTTPError, MemoryServiceError, RuntimeError) as exc:
            # Outbox row stays pending (T-6: replayed until the store acks).
            _note_background_ltm_failure(
                payload.tenant, payload.key, outbox_event_id, exc
            )
            raise _map_memory_error(exc) from exc
        except Exception as exc:
            logger.exception("Unexpected store failure: %s", exc)
            _note_background_ltm_failure(
                payload.tenant, payload.key, outbox_event_id, exc
            )
            raise HttpError(500, f"store failed: {exc}")

    # Replay anything still pending for this tenant (C1-8: pending is not a
    # dead end). Same store write, same mark-on-ack. Best effort — this call
    # already has its own durable accept.
    try:
        await _replay_pending_to_store(memsvc, payload.tenant)
    except Exception as exc:
        logger.warning("Outbox replay pass failed for tenant=%s: %s", payload.tenant, exc)

    coordinate_list = _serialize_coord(coord)
    if coordinate_list is not None:
        stored_payload["coordinate"] = coordinate_list

    promoted_to_wm = False
    warnings: list[str] = []
    tiered_vector = None

    try:
        # Embedder is usually sync or CPU bound
        vec = np.asarray(embedder.embed(seed_text), dtype=np.float32)
        if wm:
            wm.admit(payload.tenant, vec, stored_payload)
            promoted_to_wm = True
        tiered_vector = vec
    except Exception as exc:
        warnings.append(f"working-memory-admit-failed:{exc}")

    # Metrics
    try:
        if wm:
            items = len(wm.items(payload.tenant))
            record_memory_snapshot(payload.tenant, payload.namespace, items=items)
    except Exception:
        pass

    signal_feedback = MemorySignalFeedback(
        importance=signal_data.get("importance"),
        novelty=signal_data.get("novelty"),
        ttl_seconds=signal_data.get("ttl_seconds"),
        reinforcement=signal_data.get("reinforcement"),
        recall_bias=signal_data.get("recall_bias"),
        promoted_to_wm=promoted_to_wm,
        persisted_to_ltm=persisted_to_ltm,
    )

    # Surface prior background LTM persist failures on THIS call so a silent
    # loss cannot hide behind a later clean write.
    prior_failures = _background_ltm_failures.get(payload.tenant, 0)
    if prior_failures:
        warnings.append(
            f"ltm-persist:background-failures:{prior_failures}"
            ":outbox-rows-still-replayable"
        )

    # ok == durable accept (T-6): in LTM, or a verified durable outbox row.
    # degraded_journal is NOT either of those.
    durable_accept = persisted_to_ltm or durability == MemoryDurability.DURABLE_OUTBOX

    return {
        "ok": durable_accept,
        "tenant": payload.tenant,
        "namespace": payload.namespace,
        "key": payload.key,
        "coord": (
            f"{coordinate_list[0]},{coordinate_list[1]},{coordinate_list[2]}"
            if coordinate_list
            else None
        ),
        "coordinate": coordinate_list,
        "store": "somafractalmemory",
        # Report the kind that was actually stored. ``payload.kind`` is None
        # when the caller omitted it and the stored value came from
        # ``value.kind`` or the seam default.
        "kind": stored_payload.get("kind"),
        "error": None
        if durable_accept
        else "write journaled for replay but not accepted into LTM or the durable outbox",
        "durability": durability,
        "outbox_event_id": outbox_event_id,
        "promoted_to_wm": promoted_to_wm,
        "persisted_to_ltm": persisted_to_ltm,
        "queued_for_ltm": queued_for_ltm,
        "deduplicated": False,
        "importance": signal_feedback.importance,
        "novelty": signal_feedback.novelty,
        "ttl_applied": signal_feedback.ttl_seconds,
        "trace_id": payload.trace_id,
        "request_id": request_id,
        "warnings": degraded_warnings + warnings,
        "signals": signal_feedback,
    }


@router.post("/remember/batch", response=MemoryBatchWriteResponse, auth=api_key_auth)
async def remember_memory_batch(request: HttpRequest, payload: MemoryBatchWriteRequest):
    """Store multiple memories in batch."""
    require_auth(request, settings)
    # Credential tenant is the sole authority; payload.tenant is an assertion.
    payload.tenant = bind_credential_tenant(request, payload.tenant)
    pool = _get_memory_pool()
    wm = _get_wm()
    embedder = _get_embedder()

    if not pool:
        raise HttpError(503, "Memory services not available")

    resolved_ns = _resolve_namespace(payload.tenant, payload.namespace)
    memsvc = MemoryService(pool, resolved_ns)
    memsvc._reset_circuit_if_needed()

    actor = request.headers.get("X-Actor") or "memory-api"
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    item_contexts = []

    for item in payload.items:
        stored_payload, signal_data, seed_text = _compose_memory_payload(
            tenant=payload.tenant,
            namespace=payload.namespace,
            key=item.key,
            value=item.value,
            meta=item.meta,
            universe=item.universe or payload.universe,
            attachments=item.attachments,
            links=item.links,
            tags=item.tags,
            policy_tags=item.policy_tags,
            signals=item.signals,
            importance=item.importance,
            novelty=item.novelty,
            ttl_seconds=item.ttl_seconds,
            trace_id=item.trace_id,
            actor=actor,
        )
        vector = None
        warnings = []
        try:
            vector = np.asarray(embedder.embed(seed_text), dtype=np.float32)
        except Exception as exc:
            warnings.append(f"working-memory-embed-failed:{exc}")

        item_contexts.append(
            {
                "key": item.key,
                "payload": stored_payload,
                "signal_data": signal_data,
                "seed_text": seed_text,
                "trace_id": item.trace_id,
                "vector": vector,
                "warnings": warnings,
            }
        )

    if not item_contexts:
        return {
            "ok": True,
            "tenant": payload.tenant,
            "namespace": payload.namespace,
            "results": [],
        }

    # T-6: durable accept for EVERY item BEFORE the store hop. No item is
    # allowed to reach the store without a verified outbox row.
    outbox_ids: list[int] = []
    try:
        for ctx in item_contexts:
            item_coord = None
            try:
                item_coord = memsvc.client().coord_for_key(ctx["key"], None)
            except Exception:
                item_coord = None
            outbox_ids.append(
                await _durable_accept(
                    tenant=payload.tenant,
                    key=ctx["key"],
                    stored_payload=ctx["payload"],
                    request_id=f"{request_id}:{len(outbox_ids)}",
                    coord=item_coord,
                )
            )
    except HttpError:
        raise
    except Exception as exc:
        logger.error("Batch durable accept failed: %s", exc, exc_info=exc)
        raise _map_memory_error(exc) from exc

    try:
        coords = await memsvc.aremember_bulk(
            [(ctx["key"], ctx["payload"]) for ctx in item_contexts], universe=None
        )
        persisted_to_ltm = True
    except (httpx.HTTPError, MemoryServiceError, RuntimeError) as exc:
        # Outbox rows stay pending — T-6: replayed until the store acks.
        for ctx, event_id in zip(item_contexts, outbox_ids):
            _note_background_ltm_failure(payload.tenant, ctx["key"], event_id, exc)
        raise _map_memory_error(exc) from exc
    except Exception as exc:
        logger.exception("Unexpected batch store failure: %s", exc)
        for ctx, event_id in zip(item_contexts, outbox_ids):
            _note_background_ltm_failure(payload.tenant, ctx["key"], event_id, exc)
        raise HttpError(500, f"store failed: {exc}")

    # Store acked the batch: close the outbox rows.
    from somabrain.db.outbox import mark_event_sent

    for event_id in outbox_ids:
        try:
            await sync_to_async(mark_event_sent)(event_id)
        except Exception:
            logger.exception(
                "Failed to mark batch outbox event id=%s sent", event_id
            )

    results = []

    for idx, ctx in enumerate(item_contexts):
        raw_coord = coords[idx] if idx < len(coords) else None
        coordinate = _serialize_coord(raw_coord)
        if coordinate:
            ctx["payload"]["coordinate"] = coordinate

        promoted_to_wm = False
        if ctx["vector"] is not None and wm:
            try:
                wm.admit(payload.tenant, ctx["vector"], ctx["payload"])
                promoted_to_wm = True
            except Exception as exc:
                ctx["warnings"].append(f"working-memory-admit-failed:{exc}")

        signal_feedback = MemorySignalFeedback(
            importance=ctx["signal_data"].get("importance"),
            novelty=ctx["signal_data"].get("novelty"),
            ttl_seconds=ctx["signal_data"].get("ttl_seconds"),
            reinforcement=ctx["signal_data"].get("reinforcement"),
            recall_bias=ctx["signal_data"].get("recall_bias"),
            promoted_to_wm=promoted_to_wm,
            persisted_to_ltm=persisted_to_ltm,
        )
        results.append(
            {
                "key": ctx["key"],
                "coordinate": coordinate,
                "promoted_to_wm": promoted_to_wm,
                "persisted_to_ltm": persisted_to_ltm,
                "deduplicated": False,
                "importance": signal_feedback.importance,
                "novelty": signal_feedback.novelty,
                "ttl_applied": signal_feedback.ttl_seconds,
                "trace_id": ctx["trace_id"],
                "request_id": f"{request_id}:{idx}",
                "warnings": ctx["warnings"],
                "signals": signal_feedback,
            }
        )

    try:
        if wm:
            items = len(wm.items(payload.tenant))
            record_memory_snapshot(payload.tenant, payload.namespace, items=items)
    except Exception:
        pass

    return {
        "ok": True,
        "tenant": payload.tenant,
        "namespace": payload.namespace,
        "results": results,
    }
