"""Utility methods for SomaBrain memory client.

This module contains utility functions extracted from MemoryClient
to reduce file size while maintaining the same functionality.
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Tuple, TYPE_CHECKING

from somabrain.memory.normalization import _stable_coord
from somabrain.memory.transport import _response_json

if TYPE_CHECKING:
    import httpx


def get_tenant_namespace(
    cfg: Any, override_namespace: str | None = None
) -> tuple[str, str]:
    """Resolve tenant and namespace from cfg/settings with hard requirements.

    The namespace string may be in format 'base:tenant:namespace' or just 'namespace'.
    This function extracts the tenant from the namespace string if present.

    SECURITY: Correct tenant extraction is critical for multi-tenant isolation.
    See Requirements D1.1, D1.2, D1.3, D1.4.

    CRITICAL: This function MUST NEVER return an empty tenant string.
    Empty tenant would cause cross-tenant data leakage.
    """
    from django.conf import settings

    # First try explicit tenant field from config object/mock
    tenant = getattr(cfg, "tenant", None)
    if tenant:
        tenant = str(tenant).strip()

    # Get namespace from override, config, or settings
    namespace = (
        override_namespace
        or getattr(cfg, "namespace", None)
        or getattr(settings, "namespace", "public")
    )
    namespace = str(namespace or "public").strip()

    # If no explicit tenant, try to extract from namespace string
    # Namespace format: 'base:tenant:namespace' or 'base:tenant' or just 'namespace'
    if not tenant and ":" in namespace:
        parts = namespace.split(":")
        if len(parts) >= 2:
            # Format is 'base:tenant:namespace' or 'base:tenant'
            tenant = parts[1].strip()  # Second part is tenant
        elif len(parts) == 1:
            tenant = parts[0].strip()

    # Fallback to default tenant from settings
    if not tenant:
        tenant = getattr(settings, "SOMABRAIN_DEFAULT_TENANT", None)
        if tenant:
            tenant = str(tenant).strip()

    # CRITICAL: Final fallback - NEVER return empty tenant
    # This prevents cross-tenant data leakage (D1.4)
    if not tenant:
        tenant = "default"

    # Double-check: ensure tenant is never empty or whitespace-only
    tenant = tenant if tenant and tenant.strip() else "default"

    return tenant, namespace


def coord_for_key(key: str, universe: str | None = None) -> Tuple[float, float, float]:
    """Return a deterministic coordinate for *key* and optional *universe*.

    This is a lightweight helper used by migration scripts and
    higher-level services. It mirrors the stable hash used for remembered
    payloads.
    """
    uni = universe or "real"
    return _stable_coord(f"{uni}::{key}")


def fetch_by_coord(
    client: "httpx.Client | None",
    coord: Tuple[float, float, float],
) -> List[Dict[str, Any]]:
    """Fetch memory payloads by coordinate using GET /memories/{coord}.

    Returns a list of payload dicts for the given coordinate. Returns an
    empty list if no memory exists at that coordinate or if the request fails.
    """
    if client is None:
        return []
    try:
        coord_str = f"{coord[0]},{coord[1]},{coord[2]}"
        endpoint = f"/memories/{coord_str}"
        r = client.get(endpoint)
        status = int(getattr(r, "status_code", 0) or 0)
        if status == 404:
            return []
        if status != 200:
            return []
        data = _response_json(r)
        if data is None:
            return []
        # Handle various response formats
        if isinstance(data, dict):
            payload = data.get("payload")
            if isinstance(payload, dict):
                return [payload]
            memory = data.get("memory")
            if isinstance(memory, dict):
                return [memory.get("payload") or memory]
            if "task" in data or "fact" in data or "text" in data:
                return [data]
        if isinstance(data, list):
            return [p for p in data if isinstance(p, dict)]
        return []
    except Exception:
        return []


def store_from_payload(
    payload: dict,
    request_id: str | None,
    store_http_sync_fn: callable,
    remember_fn: callable,
) -> bool:
    """Store a payload dict into the memory backend.

    Tests and migration scripts call this helper. If the payload contains a
    concrete ``coordinate`` value we send it directly to the memory service.
    Otherwise we fall back to calling remember with a generated key
    derived from common payload fields.
    """
    try:
        coord = payload.get("coordinate")
        if coord is not None:
            try:
                c = (float(coord[0]), float(coord[1]), float(coord[2]))
            except Exception:
                return False
            rid = request_id or str(uuid.uuid4())
            headers = {"X-Request-ID": rid}
            body = {
                "coord": f"{c[0]},{c[1]},{c[2]}",
                "payload": dict(payload),
                "memory_type": str(
                    payload.get("memory_type") or payload.get("type") or "episodic"
                ),
            }
            success, _ = store_http_sync_fn(body, headers)
            return success

        key = (
            payload.get("task")
            or payload.get("headline")
            or payload.get("id")
            or f"autokey:{uuid.uuid4()}"
        )
        remember_fn(str(key), payload, request_id=request_id)
        return True
    except Exception:
        return False
