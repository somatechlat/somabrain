"""RAG (Retrieve-And-Guide) API for SomaBrain."""

from __future__ import annotations

import time
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

import somabrain.metrics as M
from somabrain.context.memory_shim import MemoryRecallClient
from somabrain.api.dependencies.utility_guard import utility_guard
from somabrain.api.dependencies.auth import auth_guard
from somabrain.context import ContextBuilder, ContextBundle
from somabrain.context.builder import RetrievalWeights
from somabrain.embeddings import TinyDeterministicEmbedder
from somabrain.runtime.working_memory import WorkingMemoryBuffer

router = APIRouter()
_embedder = TinyDeterministicEmbedder(dim=256)
_working_memory = WorkingMemoryBuffer()
_weights = RetrievalWeights()


def _builder_for_request() -> ContextBuilder:
    # Use canonical MemoryClient via shim; base URL and token come from central config
    memstore = MemoryRecallClient()
    return ContextBuilder(
        embed_fn=_embedder.embed,
        memstore=memstore,
        weights=_weights,
        working_memory=_working_memory,
    )


class RAGRequest(BaseModel):
    query: str | None = None
    text: str | None = None
    top_k: int = 5
    session_id: Optional[str] = None


class MemoryItem(BaseModel):
    id: str
    score: float
    metadata: dict
    embedding: List[float] | None = None


class RAGResponse(BaseModel):
    query: str
    prompt: str
    memories: List[MemoryItem]
    weights: List[float]
    residual_vector: List[float]
    working_memory: List[dict]
    latency_seconds: float


@router.post("/rag", response_model=RAGResponse)
async def rag_endpoint(
    req: RAGRequest,
    http_request: Request,
    _guard=Depends(utility_guard),
    auth=Depends(auth_guard),
):
    start = time.perf_counter()
    try:
        _ = float(getattr(http_request.state, "utility_value", 0.0))
    except Exception:
        pass

    M.RAG_REQUESTS.labels(namespace="local", retrievers="memstore").inc()
    input_text = req.query if req.query is not None else req.text or ""
    if not input_text:
        raise HTTPException(status_code=422, detail="query/text is required")

    session_id = req.session_id or http_request.headers.get("X-Session-ID")
    builder = _builder_for_request()
    try:
        bundle: ContextBundle = builder.build(
            query=input_text,
            top_k=req.top_k,
            session_id=session_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"context build failed: {exc}")

    total_lat = max(0.0, time.perf_counter() - start)
    M.RAG_RETRIEVE_LAT.observe(total_lat)

    return RAGResponse(
        query=bundle.query,
        prompt=bundle.prompt,
        memories=[MemoryItem(**r.__dict__) for r in bundle.memories],
        weights=bundle.weights,
        residual_vector=bundle.residual_vector,
        working_memory=bundle.working_memory_snapshot,
        latency_seconds=total_lat,
    )
