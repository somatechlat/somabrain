"""RAG (Retrieve-and-Generate) router.

Provides a thin wrapper endpoint for retrieval-augmented generation. The
router delegates the heavy lifting to `somabrain.services.rag_pipeline.run_rag_pipeline`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Request

from somabrain.auth import require_auth
from somabrain.config import load_config
from somabrain.schemas import RAGRequest, RAGResponse
from somabrain.tenant import get_tenant

if TYPE_CHECKING:
    # runtime-only imports omitted for static analysis
    pass

router = APIRouter()


@router.post("/retrieve", response_model=RAGResponse)
async def rag_retrieve(
    req: RAGRequest, request: Request
) -> RAGResponse:  # pragma: no cover - thin router
    """Handle a retrieval+generation request.

    The endpoint validates tenant and auth headers, extracts the optional
    universe and trace id, and forwards the request to the RAG pipeline.

    Returns the pipeline's RAGResponse on success.
    """
    cfg = load_config()
    ctx = get_tenant(request, cfg.namespace)
    require_auth(request, cfg)
    # namespace header is part of ctx; universe can be in body or header
    header_u = request.headers.get("X-Universe", "").strip() or None
    universe = req.universe or header_u
    trace_id = request.headers.get("X-Request-ID") or str(id(request))
    # Import the pipeline lazily to avoid heavy imports at module import time
    from somabrain.services.rag_pipeline import run_rag_pipeline

    resp = await run_rag_pipeline(
        req, ctx=ctx, cfg=cfg, universe=universe, trace_id=trace_id
    )
    return resp
