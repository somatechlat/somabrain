"""Link router: lightweight API for creating semantic/graph links.

Exposes a single POST /link endpoint which accepts a LinkRequest and
creates a normalized relation between two coordinates or keys in the
semantic memory service.

This module keeps the router thin and defers heavy work to
`somabrain.services.memory_service`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Request

from somabrain.auth import require_auth
from somabrain.schemas import LinkRequest, LinkResponse
from somabrain.semgraph import normalize_relation
from somabrain.tenant import get_tenant as get_tenant_async

if TYPE_CHECKING:
    # Import heavy/runtime-only types only for type checking and docs

router = APIRouter()


def _parse_coord(val):
    if isinstance(val, str):
        parts = val.split(",")
        if len(parts) == 3:
            return (float(parts[0]), float(parts[1]), float(parts[2]))
    if isinstance(val, (list, tuple)) and len(val) == 3:
        return (float(val[0]), float(val[1]), float(val[2]))
    return None


@router.post("/link", response_model=LinkResponse)
async def link(body: LinkRequest, request: Request) -> LinkResponse:
    """Create a relation (link) between two coordinates or keys.

    The endpoint accepts either explicit 3D coordinates or memory keys for
    the `from` and `to` endpoints. If keys are supplied, they are mapped to
    coordinates via the memory service. The link type is normalized using
    `somabrain.semgraph.normalize_relation` and the optional weight is used
    when inserting the link.

    Returns a simple LinkResponse(ok=True) on success.
    """
    # Import cfg and mt_memory lazily to avoid circular import at module load time
    from somabrain.app import cfg, mt_memory
    from somabrain.services.memory_service import MemoryService

    ctx = await get_tenant_async(request, cfg.namespace)
    require_auth(request, cfg)
    memsvc = MemoryService(mt_memory, ctx.namespace)

    universe = str(getattr(body, "universe", None) or "real")
    fc = _parse_coord(getattr(body, "from_coord", None))
    tc = _parse_coord(getattr(body, "to_coord", None))
    if fc is None and getattr(body, "from_key", None):
        fc = memsvc.coord_for_key(str(getattr(body, "from_key")), universe=universe)
    if tc is None and getattr(body, "to_key", None):
        tc = memsvc.coord_for_key(str(getattr(body, "to_key")), universe=universe)
    if fc is None or tc is None:
        raise Exception("missing from/to coords or keys")
    link_type = normalize_relation(str(getattr(body, "type", None) or "related"))
    weight = float(getattr(body, "weight", None) or 1.0)
    await memsvc.alink(fc, tc, link_type=link_type, weight=weight)
    return LinkResponse(ok=True)
