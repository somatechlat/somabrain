from __future__ import annotations

from fastapi import APIRouter, Request

from somabrain.auth import require_auth
from somabrain.config import load_config
from somabrain.schemas import RAGRequest, RAGResponse
from somabrain.services.rag_pipeline import run_rag_pipeline
from somabrain.tenant import get_tenant

router = APIRouter()


@router.post("/retrieve", response_model=RAGResponse)
async def rag_retrieve(
    req: RAGRequest, request: Request
) -> RAGResponse:  # pragma: no cover - thin router
    cfg = load_config()
    ctx = get_tenant(request, cfg.namespace)
    require_auth(request, cfg)
    # namespace header is part of ctx; universe can be in body or header
    header_u = request.headers.get("X-Universe", "").strip() or None
    universe = req.universe or header_u
    trace_id = request.headers.get("X-Request-ID") or str(id(request))
    resp = await run_rag_pipeline(
        req, ctx=ctx, cfg=cfg, universe=universe, trace_id=trace_id
    )
    return resp
