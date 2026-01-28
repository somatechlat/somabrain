"""Remember operations for SomaBrain memory client.

This module contains the core remember (store) operations extracted from
MemoryClient to reduce file size while maintaining the same functionality.
Functions accept transport and config directly for simpler integration.

Per Requirements E2.1-E2.4:
- E2.1: Record to outbox before SFM call
- E2.2: Mark "sent" on success
- E2.3: Remain "pending" on failure for retry
- E2.4: Duplicate detection via idempotency key
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING, Any, Callable, Iterable, List, Optional, Tuple

from somabrain.memory.normalization import _extract_memory_coord, _stable_coord
from somabrain.memory.payload import enrich_payload

if TYPE_CHECKING:
    from somabrain.memory.transport import MemoryHTTPTransport

logger = logging.getLogger(__name__)


def _record_to_outbox(
    coord: Tuple[float, float, float],
    payload: dict,
    tenant: str,
    request_id: str,
) -> Optional[int]:
    """Record memory operation to outbox before SFM call.

    Per Requirement E2.1: Record to outbox before SFM call.

    Args:
        coord: Memory coordinate
        payload: Memory payload
        tenant: Tenant ID
        request_id: Request ID for tracking

    Returns:
        Outbox event ID if recorded, None if outbox unavailable
    """
    try:
        from somabrain.db.outbox import (
            OutboxBackpressureError,
            enqueue_memory_event,
        )

        dedupe_key = enqueue_memory_event(
            topic="memory.store",
            payload={
                "coord": list(coord),
                "payload": payload,
                "request_id": request_id,
            },
            tenant_id=tenant,
            coord=coord,
            extra_key=request_id,
            check_backpressure_flag=True,
        )

        # Get the event ID for later marking
        from somabrain.db.outbox import get_event_by_dedupe_key

        event = get_event_by_dedupe_key(dedupe_key, tenant)
        return event.id if event else None

    except OutboxBackpressureError as exc:
        logger.warning(
            "Outbox backpressure, skipping outbox recording",
            pending_count=exc.pending_count,
            threshold=exc.threshold,
        )
        return None
    except Exception as exc:
        logger.debug(f"Outbox recording failed (non-critical): {exc}")
        return None


def _mark_outbox_sent(event_id: int) -> None:
    """Mark outbox event as sent after successful SFM call.

    Per Requirement E2.2: Mark "sent" on success.
    """
    try:
        from somabrain.db.outbox import mark_event_sent

        mark_event_sent(event_id)
    except Exception as exc:
        logger.debug(f"Failed to mark outbox event sent: {exc}")


def _get_tenant_namespace(cfg: Any) -> tuple[str, str]:
    """Resolve tenant and namespace from cfg/settings."""
    from django.conf import settings

    tenant = getattr(cfg, "tenant", None) or getattr(
        settings, "SOMABRAIN_DEFAULT_TENANT", "public"
    )
    namespace = getattr(cfg, "namespace", None) or getattr(
        settings, "SOMABRAIN_NAMESPACE", "public"
    )
    return str(tenant or "public"), str(namespace or "public")


def remember_sync_persist(
    transport: "MemoryHTTPTransport",
    cfg: Any,
    coord_key: str,
    payload: dict,
    request_id: str | None,
    store_http_sync_fn: Callable,
) -> Tuple[float, float, float] | None:
    """Synchronous persistence implementation for remember operations.

    Per Requirements E2.1-E2.4:
    - Records to outbox before SFM call
    - Marks "sent" on success
    - Leaves "pending" on failure for retry
    """
    if transport is None or transport.client is None:
        raise RuntimeError("HTTP memory service required for persistence")

    tenant, namespace = _get_tenant_namespace(cfg)
    enriched, uni, compat_hdr = enrich_payload(
        payload, coord_key, namespace, tenant=tenant
    )
    sc = _stable_coord(f"{uni}::{coord_key}")

    coord_str = f"{sc[0]},{sc[1]},{sc[2]}"
    body: dict[str, Any] = {
        "coord": coord_str,
        "payload": dict(enriched),
        "memory_type": str(
            payload.get("memory_type") or payload.get("type") or "episodic"
        ),
    }

    rid = request_id or str(uuid.uuid4())
    rid_hdr = {"X-Request-ID": rid}
    rid_hdr.update(compat_hdr)

    # E2.1: Record to outbox before SFM call
    outbox_event_id = _record_to_outbox(sc, enriched, tenant, rid)

    stored = False
    response_payload: Any = None
    try:
        stored, response_payload = store_http_sync_fn(body, rid_hdr)
    except Exception:
        stored = False

    server_coord: Tuple[float, float, float] | None = None
    if stored and response_payload is not None:
        try:
            server_coord = _extract_memory_coord(response_payload, idempotency_key=rid)
        except Exception:
            server_coord = None

        # E2.2: Mark outbox event as sent on success
        if outbox_event_id is not None:
            _mark_outbox_sent(outbox_event_id)

    # E2.3: If not stored, outbox entry remains "pending" for retry
    if not stored:
        msg = f"Memory service unavailable (remember persist failed). Details: {response_payload}"
        raise RuntimeError(msg)
    return server_coord


async def aremember_background(
    transport: "MemoryHTTPTransport",
    cfg: Any,
    coord_key: str,
    payload: dict,
    request_id: str | None,
    store_http_async_fn: Callable,
) -> None:
    """Async background persistence using the AsyncClient.

    Per Requirements E2.1-E2.4:
    - Records to outbox before SFM call
    - Marks "sent" on success
    - Leaves "pending" on failure for retry
    """
    if transport is None or transport.async_client is None:
        return

    rid = request_id or str(uuid.uuid4())
    rid_hdr = {"X-Request-ID": rid}
    tenant, namespace = _get_tenant_namespace(cfg)
    enriched, uni, compat_hdr = enrich_payload(
        payload, coord_key, namespace, tenant=tenant
    )
    rid_hdr.update(compat_hdr)

    # Compute stable coordinate for outbox recording
    sc = _stable_coord(f"{uni}::{coord_key}")

    # VIBE FIX: Construct correct MemoryStoreRequest schema matching sync persist
    body: dict[str, Any] = {
        "coord": f"{sc[0]},{sc[1]},{sc[2]}",
        "payload": dict(enriched),
        "memory_type": str(
            payload.get("memory_type") or payload.get("type") or "episodic"
        ),
    }

    # E2.1: Record to outbox before SFM call
    outbox_event_id = _record_to_outbox(sc, enriched, tenant, rid)

    try:
        ok, response_data = await store_http_async_fn(body, rid_hdr)
        if ok and response_data is not None:
            server_coord = _extract_memory_coord(response_data, idempotency_key=rid)
            if server_coord:
                try:
                    payload["coordinate"] = server_coord
                except Exception:
                    pass

            # E2.2: Mark outbox event as sent on success
            if outbox_event_id is not None:
                _mark_outbox_sent(outbox_event_id)
        elif not ok:
            logger.error(
                "Background memory persist schema/logic failure",
                extra={"status": "failed", "response": response_data, "rid": rid},
            )
    except Exception:
        # E2.3: Outbox entry remains "pending" for retry
        logger.exception("Background memory persist failed")


def prepare_bulk_items(
    cfg: Any,
    items: Iterable[tuple[str, dict[str, Any]]],
) -> tuple[List[dict], List[str], List[Tuple[float, float, float]], str, str]:
    """Prepare bulk items for remember_bulk operations.

    Returns: (prepared, universes, coords, tenant, namespace)
    """
    records = list(items)
    if not records:
        return [], [], [], "", ""

    prepared: List[dict[str, Any]] = []
    universes: List[str] = []
    coords: List[Tuple[float, float, float]] = []
    tenant, namespace = _get_tenant_namespace(cfg)
    cfg_namespace = getattr(cfg, "namespace", None)

    for coord_key, payload in records:
        enriched, universe, _ = enrich_payload(
            payload, coord_key, cfg_namespace, tenant=tenant
        )
        coord = _stable_coord(f"{universe}::{coord_key}")
        body: dict[str, Any] = {
            "tenant": tenant,
            "namespace": namespace,
            "key": coord_key,
            "value": dict(enriched),
            "universe": universe,
        }
        for optional_key in (
            "meta",
            "ttl_seconds",
            "tags",
            "policy_tags",
            "attachments",
            "links",
            "signals",
            "importance",
            "novelty",
            "trace_id",
        ):
            if isinstance(payload, dict) and optional_key in payload:
                body[optional_key] = payload.get(optional_key)
        universes.append(universe)
        coords.append(coord)
        prepared.append(
            {
                "coord_key": coord_key,
                "body": body,
                "universe": universe,
            }
        )

    return prepared, universes, coords, tenant, namespace


def process_bulk_response(
    response: Any,
    prepared: List[dict],
    coords: List[Tuple[float, float, float]],
    rid: str,
) -> List[Tuple[float, float, float]]:
    """Process bulk response and update coords with server coordinates."""
    returned: List[Any] = []
    if isinstance(response, dict):
        for key in ("items", "results", "memories", "entries"):
            seq = response.get(key)
            if isinstance(seq, list):
                returned = seq
                break
    elif isinstance(response, list):
        returned = response

    for idx, entry in enumerate(returned[: len(prepared)]):
        server_coord = _extract_memory_coord(entry, idempotency_key=f"{rid}:{idx}")
        if server_coord:
            coords[idx] = server_coord

    return coords


async def aremember_single(
    cfg: Any,
    coord_key: str,
    payload: dict,
    request_id: str | None,
    require_healthy_fn: Callable,
    store_http_async_fn: Callable,
    enrich_payload_fn: Callable,
    has_async_transport: bool,
) -> Tuple[float, float, float]:
    """Async variant of remember for HTTP mode.

    Args:
        cfg: Configuration object.
        coord_key: Key for coordinate generation.
        payload: Memory payload.
        request_id: Optional request ID for tracing.
        require_healthy_fn: Function to check SFM health.
        store_http_async_fn: Async function to store memory.
        enrich_payload_fn: Function to enrich payload.
        has_async_transport: Whether async HTTP transport is available.

    Returns:
        Coordinate tuple for stored memory.
    """
    require_healthy_fn()

    if not has_async_transport:
        raise RuntimeError("Async memory transport unavailable")

    enriched, universe, compat_hdr = enrich_payload_fn(payload, coord_key)
    coord = _stable_coord(f"{universe}::{coord_key}")
    enriched = dict(enriched)
    enriched.setdefault("coordinate", coord)
    memory_type = str(
        enriched.get("memory_type") or enriched.get("type") or "episodic"
    )
    body = {
        "coord": f"{coord[0]},{coord[1]},{coord[2]}",
        "payload": enriched,
        "memory_type": memory_type,
    }
    rid = request_id or str(uuid.uuid4())
    rid_hdr = {"X-Request-ID": rid}
    rid_hdr.update(compat_hdr)
    ok, response_data = await store_http_async_fn(body, rid_hdr)
    if ok and response_data is not None:
        server_coord = _extract_memory_coord(response_data, idempotency_key=rid)
        if server_coord:
            return server_coord
    raise RuntimeError("Memory store failed: no server coordinate returned")
