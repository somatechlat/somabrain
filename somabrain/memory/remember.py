"""Remember operations for SomaBrain memory client.

This module contains the core remember (store) operations extracted from
MemoryClient to reduce file size while maintaining the same functionality.
Functions accept transport and config directly for simpler integration.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Iterable, List, Tuple, TYPE_CHECKING

from somabrain.memory.normalization import _stable_coord, _extract_memory_coord
from somabrain.memory.payload import enrich_payload, prepare_memory_payload

if TYPE_CHECKING:
    from somabrain.memory.transport import MemoryHTTPTransport

logger = logging.getLogger(__name__)


def _get_tenant_namespace(cfg: Any) -> tuple[str, str]:
    """Resolve tenant and namespace from cfg/settings."""
    from common.config.settings import settings

    tenant = getattr(cfg, "tenant", None) or getattr(
        settings, "default_tenant", "public"
    )
    namespace = getattr(cfg, "namespace", None) or getattr(
        settings, "namespace", "public"
    )
    return str(tenant or "public"), str(namespace or "public")


def remember_sync_persist(
    transport: "MemoryHTTPTransport",
    cfg: Any,
    coord_key: str,
    payload: dict,
    request_id: str | None,
    store_http_sync_fn: callable,
) -> Tuple[float, float, float] | None:
    """Synchronous persistence implementation for remember operations."""
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

    if not stored:
        raise RuntimeError("Memory service unavailable (remember persist failed)")
    return server_coord


async def aremember_background(
    transport: "MemoryHTTPTransport",
    cfg: Any,
    coord_key: str,
    payload: dict,
    request_id: str | None,
    store_http_async_fn: callable,
) -> None:
    """Async background persistence using the AsyncClient."""
    if transport is None or transport.async_client is None:
        return

    rid = request_id
    rid_hdr = {"X-Request-ID": rid} if rid else {}
    tenant, namespace = _get_tenant_namespace(cfg)
    enriched, uni, compat_hdr = enrich_payload(
        payload, coord_key, namespace, tenant=tenant
    )
    rid_hdr.update(compat_hdr)
    ns = namespace

    body: dict[str, Any] = {
        "tenant": tenant,
        "namespace": ns,
        "key": coord_key,
        "value": enriched,
        "universe": uni,
        "trace_id": payload.get("trace_id") if isinstance(payload, dict) else None,
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
    ):
        if isinstance(payload, dict) and optional_key in payload:
            body[optional_key] = payload.get(optional_key)

    try:
        ok, response_data = await store_http_async_fn(body, rid_hdr)
        if ok and response_data is not None:
            server_coord = _extract_memory_coord(response_data, idempotency_key=rid)
            if server_coord:
                try:
                    payload["coordinate"] = server_coord
                except Exception:
                    pass
    except Exception:
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
