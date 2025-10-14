from __future__ import annotations

import hashlib
import json
import time
from typing import TYPE_CHECKING, Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException, Request, Response

from somabrain.auth import require_auth
from somabrain.config import get_config
from somabrain.schemas import Persona
from somabrain.tenant import get_tenant

if TYPE_CHECKING:
    # runtime-only imports omitted for doc builds and static analysis
    pass

router = APIRouter(prefix="/persona")


def _compute_etag(payload: Dict[str, Any]) -> str:
    j = json.dumps(payload or {}, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(j.encode("utf-8")).hexdigest()


@router.put("/{pid}")
async def put_persona(
    pid: str,
    persona: Persona,
    request: Request,
    response: Response,
    if_match: Optional[str] = Header(None),
):
    """Create or update a Persona record.

    Uses optimistic CAS if the client supplies an If-Match header containing the
    current ETag. Returns an ETag header for the newly stored representation.
    """
    cfg = get_config()
    ctx = get_tenant(request, cfg.namespace)
    require_auth(request, cfg)

    # import runtime lazily to avoid circular imports at module load
    from somabrain import runtime as _rt
    from somabrain.services.memory_service import MemoryService as _MS

    # Robustness: if runtime.mt_memory is missing (import ordering), fall back to app.mt_memory or a local instance
    mem_backend = getattr(_rt, "mt_memory", None)
    if mem_backend is None:
        try:
            import somabrain.app as _app_mod

            mem_backend = getattr(_app_mod, "mt_memory", None) or mem_backend
        except Exception:
            mem_backend = None
    if mem_backend is None:
        try:
            from somabrain.config import get_config as _get_cfg
            from somabrain.memory_pool import MultiTenantMemory

            mem_backend = MultiTenantMemory(_get_cfg())
            try:
                setattr(_rt, "mt_memory", mem_backend)
            except Exception:
                pass
        except Exception:
            mem_backend = None
    ms = _MS(mem_backend, ctx.namespace)
    key = f"persona:{pid}"

    # lookup existing persona payload (best-effort)
    coord = ms.coord_for_key(key)
    try:
        existing = ms.payloads_for_coords([coord]) or []
    except Exception:
        existing = []

    # Find most recent persona payload (exclude tombstones)
    current_payload = None
    if existing:
        # prefer payloads with fact == 'persona'
        for p in reversed(existing):
            if isinstance(p, dict) and p.get("fact") == "persona":
                current_payload = p
                break

    # CAS: if client provided If-Match, verify
    if if_match is not None:
        current_etag = _compute_etag(current_payload) if current_payload else ""
        if if_match != current_etag:
            raise HTTPException(status_code=412, detail="ETag mismatch")

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
        raise HTTPException(status_code=500, detail=str(e))
    # Sync PersonalityStore so that traits affect neuromodulation and act salience
    try:
        from somabrain.app import personality_store as _ps

        # persona.traits may be a dict; ensure proper type
        _ps.set(ctx.tenant_id, dict(persona.properties or {}))
    except Exception:
        # Non‑critical: ignore if store unavailable
        pass

    new_etag = _compute_etag(payload)
    response.headers["ETag"] = new_etag
    return {"ok": True, "persona": payload}


@router.get("/{pid}")
async def get_persona(pid: str, request: Request, response: Response):
    """Retrieve the latest Persona record for pid. Returns 404 if not found."""
    cfg = get_config()
    ctx = get_tenant(request, cfg.namespace)
    require_auth(request, cfg)

    from somabrain import runtime as _rt
    from somabrain.services.memory_service import MemoryService as _MS

    mem_backend = getattr(_rt, "mt_memory", None)
    if mem_backend is None:
        try:
            import somabrain.app as _app_mod

            mem_backend = getattr(_app_mod, "mt_memory", None) or mem_backend
        except Exception:
            mem_backend = None
    ms = _MS(mem_backend, ctx.namespace)
    key = f"persona:{pid}"
    coord = ms.coord_for_key(key)
    try:
        hits = ms.payloads_for_coords([coord]) or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # select most recent persona payload (exclude tombstones)
    for p in reversed(hits):
        if isinstance(p, dict) and p.get("fact") == "persona":
            etag = _compute_etag(p)
            response.headers["ETag"] = etag
            return p

    raise HTTPException(status_code=404, detail="persona not found")


@router.delete("/{pid}")
async def delete_persona(pid: str, request: Request):
    """Append a persona tombstone for pid. Best-effort delete for Phase 1."""
    cfg = get_config()
    ctx = get_tenant(request, cfg.namespace)
    require_auth(request, cfg)

    from somabrain import runtime as _rt
    from somabrain.services.memory_service import MemoryService as _MS

    mem_backend = getattr(_rt, "mt_memory", None)
    if mem_backend is None:
        try:
            import somabrain.app as _app_mod

            mem_backend = getattr(_app_mod, "mt_memory", None) or mem_backend
        except Exception:
            mem_backend = None
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
        raise HTTPException(status_code=500, detail=str(e))
    return {"ok": True}
