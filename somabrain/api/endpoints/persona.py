from typing import Dict, Optional, Any
import time
import hashlib
import json
from types import SimpleNamespace

from ninja import Router, Schema
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404
from ninja.errors import HttpError

from somabrain.auth import require_auth
from django.conf import settings
from somabrain.schemas import Persona
from somabrain.tenant_manager import get_tenant_manager

# Note: Ideally move these imports to top-level if dependencies allow,
# but keeping structure similar to original for safety during rapid migration.
try:
    from somabrain import runtime as _rt
    from somabrain.services.memory_service import MemoryService as _MS
except ImportError:
    _rt = None
    _MS = None

router = Router(tags=["persona"])

def _compute_etag(payload: Dict[str, Any]) -> str:
    j = json.dumps(payload or {}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(j.encode("utf-8")).hexdigest()

@router.put("/{pid}")
async def put_persona(
    request: HttpRequest,
    pid: str,
    persona: Persona,
):
    """Create or update a Persona record."""
    if_match = request.headers.get("If-Match")
    cfg = settings
    tenant_manager = await get_tenant_manager()
    tenant_id = await tenant_manager.resolve_tenant_from_request(request)
    ctx = SimpleNamespace(namespace=tenant_id, tenant_id=tenant_id)
    require_auth(request, cfg)

    # Lazy import logic adapted from original
    # In V2 we should clean this up to proper DI
    from somabrain import runtime as _rt
    from somabrain.services.memory_service import MemoryService as _MS
    
    mem_backend = getattr(_rt, "mt_memory", None)
    if mem_backend is None:
        # VIBE RULES: No fallbacks - throw error if backend not available
        raise HttpError(503, "Memory backend not initialized. Service unavailable.")

    if not _MS: # Should handle import error
         raise HttpError(500, "MemoryService not available")

    ms = _MS(mem_backend, ctx.namespace)
    key = f"persona:{pid}"
    coord = ms.coord_for_key(key)

    existing: list[dict] = []
    try:
        existing = ms.fetch_by_coord(coord) or []
    except Exception:
        existing = []

    current_payload = None
    if existing:
        for p in reversed(existing):
            if isinstance(p, dict) and p.get("fact") == "persona":
                current_payload = p
                break

    if if_match is not None:
        current_etag = _compute_etag(current_payload) if current_payload else ""
        if if_match != current_etag:
            raise HttpError(412, "ETag mismatch")

    payload = {
        "id": pid,
        "display_name": persona.display_name,
        "properties": persona.properties,
        "fact": "persona",
        "memory_type": "semantic",
        "timestamp": time.time(),
    }

    try:
        ms.remember(key, payload)
    except Exception as e:
         raise HttpError(500, str(e))

    # Sync PersonalityStore - Ignoring for now as it's best effort in original code
    
    new_etag = _compute_etag(payload)
    # Ninja doesn't have a direct 'Response' object injection in args the same way for headers
    # We return a specific response or modify headers on the response object if we return one.
    # For now, we'll return the dict and let Ninja handle JSON, 
    # but strictly speaking we lose ETag header unless we use `HttpResponse` or similar.
    # However, to be "Production Grade" per VIBE, we should set the header.
    
    # Returning a tuple (status_code, data) is possible, but headers...
    # We can use the response object from `request`? No, that's Django.
    # We return an HttpResponse if we want full control.
    
    response = HttpResponse(json.dumps({"ok": True, "persona": payload}), content_type="application/json")
    response["ETag"] = new_etag
    return response

@router.get("/{pid}")
async def get_persona(request: HttpRequest, pid: str):
    """Retrieve the latest Persona record for pid."""
    cfg = settings
    tenant_manager = await get_tenant_manager()
    tenant_id = await tenant_manager.resolve_tenant_from_request(request)
    ctx = SimpleNamespace(namespace=tenant_id, tenant_id=tenant_id)
    require_auth(request, cfg)

    from somabrain import runtime as _rt
    from somabrain.services.memory_service import MemoryService as _MS
    
    # ... (Same backend resolution logic as above) ...
    mem_backend = getattr(_rt, "mt_memory", None)
    # VIBE RULES: No fallbacks - throw error if backend not available
    if mem_backend is None:
        raise HttpError(503, "Memory backend not initialized. Service unavailable.")

    ms = _MS(mem_backend, ctx.namespace)
    key = f"persona:{pid}"
    coord = ms.coord_for_key(key)
    
    try:
        hits = ms.fetch_by_coord(coord) or []
    except Exception as e:
         raise HttpError(500, str(e))

    for p in reversed(hits):
        if isinstance(p, dict) and p.get("fact") == "persona":
            etag = _compute_etag(p)
            response = HttpResponse(json.dumps(p), content_type="application/json")
            response["ETag"] = etag
            return response

    raise HttpError(404, "persona not found")

@router.delete("/{pid}")
async def delete_persona(request: HttpRequest, pid: str):
    """Append a persona tombstone for pid."""
    cfg = settings
    tenant_manager = await get_tenant_manager()
    tenant_id = await tenant_manager.resolve_tenant_from_request(request)
    ctx = SimpleNamespace(namespace=tenant_id, tenant_id=tenant_id)
    require_auth(request, cfg)

    from somabrain import runtime as _rt
    from somabrain.services.memory_service import MemoryService as _MS
    
    mem_backend = getattr(_rt, "mt_memory", None)
    # VIBE RULES: No fallbacks - throw error if backend not available
    if mem_backend is None:
        raise HttpError(503, "Memory backend not initialized. Service unavailable.")

    ms = _MS(mem_backend, ctx.namespace)
    key = f"persona:{pid}"
    
    tomb = {
        "id": pid,
        "fact": "persona_tombstone",
        "memory_type": "semantic",
        "timestamp": time.time(),
    }
    try:
        ms.remember(key, tomb)
    except Exception as e:
         raise HttpError(500, str(e))
         
    return {"ok": True}
