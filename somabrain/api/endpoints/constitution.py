"""Module constitution."""

import logging
import time
from typing import Any, Dict
from uuid import uuid4

from django.http import HttpRequest
from ninja import Router, Schema
from ninja.errors import HttpError

from somabrain import audit
from somabrain.constitution import ConstitutionError
from somabrain.services.constitution import get_constitution_engine

LOGGER = logging.getLogger("somabrain.api.constitution")

router = Router(tags=["constitution"])


class ValidateRequest(Schema):
    """Data model for ValidateRequest."""

    input: dict


@router.get("/version")
def version(request: HttpRequest):
    """Execute version.

    Args:
        request: The request.
    """

    engine = get_constitution_engine()
    checksum = engine.get_checksum() if engine else None
    status = "loaded" if checksum else "not-loaded"
    return {
        "constitution_version": checksum,
        "constitution_status": status,
        "constitution_signatures": engine.get_signatures() if engine else [],
    }


@router.post("/validate")
def validate(request: HttpRequest, req: ValidateRequest):
    """Execute validate.

    Args:
        request: The request.
        req: The req.
    """

    engine = get_constitution_engine()
    if not engine:
        raise HttpError(503, "Constitution engine not initialized")
    try:
        result = engine.validate(req.input)
        # Emit audit event (non-blocking, best-effort)
        try:
            # Django request.user is set by auth middleware
            user = (
                str(request.user)
                if request.user.is_authenticated
                else request.headers.get("X-User")
            )

            event = {
                "event_id": str(uuid4()),
                "timestamp": int(time.time()),
                "request_id": request.headers.get("X-Request-Id") or str(uuid4()),
                "remote_addr": request.META.get("REMOTE_ADDR"),
                "user": user,
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
        raise HttpError(500, str(e))


@router.post("/load")
def load_constitution(request: HttpRequest, payload: Dict[str, Any]):
    """Save a new constitution JSON to Redis."""
    engine = get_constitution_engine()
    if not engine:
        raise HttpError(503, "Constitution engine not initialized")
    try:
        # payload is expected to be the constitution dict directly if passed as body
        # Ninja parses JSON body into the argument if type hinted.
        # However, if 'payload' is the container, we need to be careful.
        # Original endpoint expected a raw dict as body. Ninja does this if body param is not defined?
        # Let's assume payload matches the body schema.

        engine.save(payload)
        return {"status": "saved", "checksum": engine.get_checksum()}
    except ConstitutionError as e:
        raise HttpError(500, str(e))
