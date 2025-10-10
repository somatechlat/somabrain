"""SomaFractalMemory (SMF) service entrypoint.

The SMF service fronts the shared vector database (Qdrant-compatible) and
provides a narrow HTTP API tailored for SomaBrain retrieval workloads.
Requests are proxied to the configured vector endpoint so the service remains
stateless and can scale horizontally with the rest of the stack.
"""

from __future__ import annotations

import os
from typing import Any, Optional

import httpx
from fastapi import APIRouter, FastAPI, HTTPException, status
from pydantic import BaseModel, Field

DEFAULT_VECTOR_ENDPOINT = "http://vector.soma-infra.svc.cluster.local:6333"


class UpsertPoint(BaseModel):
    collection: str = Field(..., description="Vector collection name")
    point_id: str | int = Field(..., alias="id")
    vector: list[float]
    payload: dict[str, Any] | None = None

    class Config:
        allow_population_by_field_name = True


class SearchRequest(BaseModel):
    collection: str
    vector: list[float]
    limit: int = 5
    filter: Optional[dict[str, Any]] = None


class DeleteRequest(BaseModel):
    collection: str
    ids: list[str | int]


def _vector_endpoint(explicit: Optional[str] = None) -> str:
    if explicit:
        return explicit.rstrip("/")
    env_value = os.getenv("SOMABRAIN_VECTOR_ENDPOINT")
    if env_value:
        return env_value.rstrip("/")
    return DEFAULT_VECTOR_ENDPOINT.rstrip("/")


def create_app(*, vector_endpoint: Optional[str] = None) -> FastAPI:
    """Return the FastAPI app that fronts the vector store."""

    base_url = _vector_endpoint(vector_endpoint)
    app = FastAPI(
        title="SomaFractalMemory",
        description="Vector store gateway for SomaBrain embeddings (Qdrant API).",
        version="1.0.0",
    )
    router = APIRouter()

    @app.on_event("startup")
    async def _startup() -> None:
        app.state.vector_client = httpx.AsyncClient(base_url=base_url, timeout=15.0)

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        client = getattr(app.state, "vector_client", None)
        if client is not None:
            await client.aclose()

    @router.put(
        "/vectors",
        status_code=status.HTTP_202_ACCEPTED,
        summary="Upsert a single vector point into the shared collection.",
    )
    async def upsert(point: UpsertPoint) -> dict[str, Any]:
        client: httpx.AsyncClient = app.state.vector_client
        body = {
            "points": [
                {
                    "id": point.point_id,
                    "vector": point.vector,
                    "payload": point.payload or {},
                }
            ]
        }
        response = await client.put(
            f"/collections/{point.collection}/points?wait=true", json=body
        )
        if response.status_code >= 400:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.text or "vector store error",
            )
        return response.json() if response.content else {"status": "accepted"}

    @router.post(
        "/vectors/search",
        summary="Search the collection for nearest neighbours.",
    )
    async def search(req: SearchRequest) -> dict[str, Any]:
        client: httpx.AsyncClient = app.state.vector_client
        body = {
            "vector": req.vector,
            "limit": req.limit,
        }
        if req.filter:
            body["filter"] = req.filter
        response = await client.post(
            f"/collections/{req.collection}/points/search", json=body
        )
        if response.status_code >= 400:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.text or "vector store error",
            )
        return response.json()

    @router.delete(
        "/vectors",
        status_code=status.HTTP_202_ACCEPTED,
        summary="Delete vector points from the collection.",
    )
    async def delete(req: DeleteRequest) -> dict[str, Any]:
        client: httpx.AsyncClient = app.state.vector_client
        body = {"points": req.ids}
        response = await client.post(
            f"/collections/{req.collection}/points/delete?wait=true", json=body
        )
        if response.status_code >= 400:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.text or "vector store error",
            )
        return response.json() if response.content else {"status": "accepted"}

    @router.get("/healthz")
    async def healthz() -> dict[str, Any]:
        client: httpx.AsyncClient = app.state.vector_client
        try:
            resp = await client.get("/collections")
            ok = resp.status_code < 400
        except Exception:
            ok = False
        return {"status": "ok" if ok else "degraded", "vector_ok": ok}

    app.include_router(router, prefix="/api")
    return app


__all__ = ["create_app", "DEFAULT_VECTOR_ENDPOINT"]
