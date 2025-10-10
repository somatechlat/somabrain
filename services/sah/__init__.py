"""SomaAgentHub service entrypoint.

Provides a thin FastAPI orchestration layer that fronts the core SomaBrain HTTP
API and shared infrastructure services (memory, auth, OPA).  The hub exposes
light-weight management endpoints for developers while delegating all heavy
workloads to the specialised services defined in the consolidated architecture.
"""

from __future__ import annotations

import os
from typing import Any, Optional

import httpx
from fastapi import APIRouter, FastAPI, HTTPException, status
from pydantic import BaseModel

try:  # optional – legacy environments may not ship the shared settings package
    from common.config.settings import settings as shared_settings
except Exception:  # pragma: no cover
    shared_settings = None  # type: ignore

from somabrain.app import app as brain_app

DEFAULT_MEMORY_ENDPOINT = "http://memory.soma-infra.svc.cluster.local:9595"
DEFAULT_AUTH_ENDPOINT = "http://auth.soma-infra.svc.cluster.local:8080"
DEFAULT_OPA_ENDPOINT = "http://opa.soma-infra.svc.cluster.local:8181"


def _resolve_endpoint(setting_name: str, env_name: str, default: str) -> str:
    """Resolve an endpoint from shared settings, environment or fallback."""

    if shared_settings is not None:
        try:
            value = getattr(shared_settings, setting_name, None)
            if value:
                return str(value).rstrip("/")
        except Exception:
            pass
    env_value = os.getenv(env_name)
    if env_value:
        return env_value.rstrip("/")
    return default.rstrip("/")


class RememberPayload(BaseModel):
    coord_key: str
    payload: dict


class RecallRequest(BaseModel):
    query: str
    top_k: int = 3


class HealthReport(BaseModel):
    status: str
    memory_ok: bool
    auth_ok: Optional[bool] = None
    opa_ok: Optional[bool] = None


def create_app(
    *,
    memory_endpoint: Optional[str] = None,
    auth_endpoint: Optional[str] = None,
    opa_endpoint: Optional[str] = None,
) -> FastAPI:
    """Assemble and return the SomaAgentHub FastAPI application."""

    mem_ep = (memory_endpoint or _resolve_endpoint("memory_http_endpoint", "SOMABRAIN_MEMORY_HTTP_ENDPOINT", DEFAULT_MEMORY_ENDPOINT)).rstrip(
        "/"
    )
    auth_ep = (auth_endpoint or _resolve_endpoint("auth_service_url", "SOMABRAIN_AUTH_SERVICE_URL", DEFAULT_AUTH_ENDPOINT)).rstrip(
        "/"
    )
    opa_ep = (opa_endpoint or os.getenv("SOMABRAIN_OPA_ENDPOINT") or DEFAULT_OPA_ENDPOINT).rstrip(
        "/"
    )

    hub = FastAPI(
        title="SomaAgentHub",
        description="Gateway and orchestration layer for the Soma stack.",
        version="1.0.0",
    )

    router = APIRouter()

    @hub.on_event("startup")
    async def _startup() -> None:
        hub.state.memory_client = httpx.AsyncClient(base_url=mem_ep, timeout=10.0)
        hub.state.auth_client = httpx.AsyncClient(base_url=auth_ep, timeout=5.0)
        hub.state.opa_client = httpx.AsyncClient(base_url=opa_ep, timeout=5.0)

    @hub.on_event("shutdown")
    async def _shutdown() -> None:
        for attr in ("memory_client", "auth_client", "opa_client"):
            client = getattr(hub.state, attr, None)
            if client is not None:
                await client.aclose()

    @router.post("/memory/remember", status_code=status.HTTP_202_ACCEPTED)
    async def remember(req: RememberPayload) -> dict[str, Any]:
        client: httpx.AsyncClient = hub.state.memory_client
        body = {"coord": req.coord_key, "payload": req.payload}
        response = await client.post("/remember", json=body)
        if response.status_code >= 400:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.text or "memory service error",
            )
        return response.json() if response.content else {"ok": True}

    @router.post("/memory/recall")
    async def recall(req: RecallRequest) -> dict[str, Any]:
        client: httpx.AsyncClient = hub.state.memory_client
        response = await client.post(
            "/recall", json={"query": req.query, "top_k": req.top_k}
        )
        if response.status_code >= 400:
            raise HTTPException(
                status_code=response.status_code,
                detail=response.text or "memory service error",
            )
        return response.json()

    @router.get("/healthz", response_model=HealthReport)
    async def healthz() -> HealthReport:
        mem_ok = False
        auth_ok: Optional[bool] = None
        opa_ok: Optional[bool] = None

        try:
            mem_resp = await hub.state.memory_client.get("/health")
            mem_ok = mem_resp.status_code < 400
        except Exception:
            mem_ok = False

        try:
            auth_resp = await hub.state.auth_client.get("/health")
            auth_ok = auth_resp.status_code < 400
        except Exception:
            auth_ok = None

        try:
            opa_resp = await hub.state.opa_client.get("/health")
            opa_ok = opa_resp.status_code < 400
        except Exception:
            opa_ok = None

        status_text = "ok" if mem_ok else "degraded"
        return HealthReport(
            status=status_text,
            memory_ok=mem_ok,
            auth_ok=auth_ok,
            opa_ok=opa_ok,
        )

    hub.include_router(router, prefix="/api")
    hub.mount("/brain", brain_app)

    return hub


__all__ = ["create_app", "DEFAULT_MEMORY_ENDPOINT", "DEFAULT_AUTH_ENDPOINT", "DEFAULT_OPA_ENDPOINT"]
