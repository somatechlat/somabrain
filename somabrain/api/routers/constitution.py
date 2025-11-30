from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from somabrain import audit
from somabrain.constitution import ConstitutionEngine, ConstitutionError

LOGGER = logging.getLogger("somabrain.api.constitution")

router = APIRouter()


class ValidateRequest(BaseModel):
    input: dict


@router.get("/version")
async def version(request: Request):
    engine: ConstitutionEngine = request.app.state.constitution_engine
    checksum = engine.get_checksum() if engine else None
    status = "loaded" if checksum else "not-loaded"
    return {
        "constitution_version": checksum,
        "constitution_status": status,
        "constitution_signatures": engine.get_signatures() if engine else [],
    }


@router.post("/validate")
async def validate(req: ValidateRequest, request: Request):
    engine: ConstitutionEngine = request.app.state.constitution_engine
    if not engine:
        raise HTTPException(
            status_code=503, detail="Constitution engine not initialized"
        )
    try:
        result = engine.validate(req.input)
        # Emit audit event (non-blocking, best-effort)
        try:
            event = {
                "event_id": str(uuid4()),
                "timestamp": int(__import__("time").time()),
                "request_id": request.headers.get("X-Request-Id") or str(uuid4()),
                "remote_addr": request.client.host if request.client else None,
                "user": request.headers.get("X-User")
                or request.headers.get("Authorization"),
                "input": req.input,
                "decision": result.get("allowed") if isinstance(result, dict) else None,
                "violated": (
                    result.get("violations") if isinstance(result, dict) else None
                ),
                "constitution_sha": engine.get_checksum(),
                "constitution_sig": engine.get_signature(),
            }
            audit.publish_event(event)
        except Exception:
            LOGGER.exception("Failed to emit constitution audit event")
        return result
    except ConstitutionError as e:
        LOGGER.error("Constitution validation error: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/load")
async def load_constitution(payload: dict, request: Request):
    """Save a new constitution JSON to Redis.

    The endpoint expects a raw JSON object representing the constitution.
    It uses the shared ``ConstitutionEngine`` instance attached to ``app.state``.
    Returns the new checksum for verification.
    """
    engine: ConstitutionEngine = request.app.state.constitution_engine
    if not engine:
        raise HTTPException(
            status_code=503, detail="Constitution engine not initialized"
        )
    try:
        engine.save(payload)
        return {"status": "saved", "checksum": engine.get_checksum()}
    except ConstitutionError as e:
        raise HTTPException(status_code=500, detail=str(e))
