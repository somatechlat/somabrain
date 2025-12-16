"""Proxy Router
==============

Embedded service proxy endpoints for dev/test parity.
These endpoints provide a stable surface for integration tests by
proxying to the in-container services managed by Supervisor.

Endpoints:
- GET /reward/health - Check reward producer health
- GET /learner/health - Check learner health
- POST /reward/reward/{frame_id} - Forward reward to producer
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException

logger = logging.getLogger("somabrain.routers.proxy")

router = APIRouter(tags=["proxy"])


def _cog_http_base() -> str:
    """Get the base URL for the somabrain_cog container."""
    return "http://somabrain_cog"


async def _probe_service_http(path: str, port: int, *, timeout: float = 1.5) -> bool:
    """Probe a service HTTP endpoint for health."""
    try:
        import httpx

        url = f"{_cog_http_base()}:{port}{path}"
        async with httpx.AsyncClient(timeout=timeout) as cli:
            r = await cli.get(url)
            if int(getattr(r, "status_code", 0) or 0) != 200:
                return False
            try:
                j = r.json()
            except Exception:
                return True
            return bool(j.get("ok", True)) if isinstance(j, dict) else True
    except Exception:
        return False


@router.get("/reward/health")
async def reward_health() -> dict:
    """Check reward producer health via HTTP probe."""
    ok = await _probe_service_http("/health", 8083)
    if not ok:
        raise HTTPException(
            status_code=404,
            detail="Embedded reward endpoint not mounted (non-dev mode)",
        )
    return {"ok": True}


@router.get("/learner/health")
async def learner_health() -> dict:
    """Check learner health via HTTP probe."""
    ok = await _probe_service_http("/health", 8084)
    if not ok:
        raise HTTPException(
            status_code=404,
            detail="Embedded learner endpoint not mounted (non-dev mode)",
        )
    return {"ok": True}


@router.post("/reward/reward/{frame_id}")
async def post_reward_proxy(frame_id: str, body: dict) -> dict:
    """Forward reward to reward_producer HTTP in somabrain_cog."""
    try:
        import httpx

        url = f"{_cog_http_base()}:8083/reward/{frame_id}"
        async with httpx.AsyncClient(timeout=2.0) as cli:
            r = await cli.post(url, json=body)
            if r.status_code == 503:
                raise HTTPException(
                    status_code=503,
                    detail="Reward producer unavailable (Kafka not ready)",
                )
            r.raise_for_status()
            return r.json()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=503, detail="Reward producer unavailable (Kafka not ready)"
        )
