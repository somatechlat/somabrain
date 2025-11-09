import json
import logging
import os
from typing import Any, Awaitable, Callable

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

import somabrain.metrics as app_metrics
from somabrain.opa.client import opa_client, _policy_path_for_mode

try:
    from common.config.settings import settings as shared_settings
except Exception:  # pragma: no cover - optional dependency in legacy layouts
    shared_settings = None  # type: ignore

LOGGER = logging.getLogger("somabrain.api.middleware.opa")


class OpaMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that forwards request data to an OPA side‑car for policy enforcement.

    The middleware expects the environment variable ``SOMA_OPA_URL`` to contain the base URL
    of the OPA HTTP server (e.g. ``http://127.0.0.1:8181``). If the variable is not set, the
    middleware becomes a no‑op and all requests are allowed.
    """

    async def dispatch(self, request: Request, call_next):
        if shared_settings is not None:
            try:
                opa_url = getattr(shared_settings, "opa_url", None)
            except Exception:
                opa_url = None
        else:
            opa_url = None
        if not opa_url:
            opa_url = os.getenv("SOMA_OPA_URL")
        # Build minimal input payload for OPA – include request method, path and JSON body if any
        input_payload = {
            "method": request.method,
            "path": request.url.path,
        }
        # Try to read JSON body without consuming it for downstream handlers
        try:
            body_bytes = await request.body()
            if body_bytes:
                try:
                    input_payload["json"] = json.loads(body_bytes)
                except Exception:
                    # Non‑JSON body – ignore but keep raw bytes for debugging
                    input_payload["raw_body"] = body_bytes.decode(errors="ignore")

            # Re‑inject the body for downstream processing
            async def receive() -> dict:
                return {"type": "http.request", "body": body_bytes}

            request._receive = receive  # type: ignore[attr-defined]
        except Exception:
            # If reading the body fails we continue with method/path only
            pass

        # If OPA URL is not configured, fall back to local opa_client evaluation
        if not opa_url:
            try:
                allowed = opa_client.evaluate(input_payload)
                if not allowed:
                    # Increment deny metric using app_metrics
                    app_metrics.OPA_DENY_TOTAL.inc()
                    return Response(
                        content=json.dumps({"detail": "OPA policy denied request"}),
                        status_code=403,
                        media_type="application/json",
                    )
                else:
                    # Increment allow metric using app_metrics
                    app_metrics.OPA_ALLOW_TOTAL.inc()
                    return await call_next(request)
            except Exception as exc:
                # Strict: default fail-closed if OPA evaluation fails
                if shared_settings is not None:
                    try:
                        fail_closed = bool(
                            getattr(shared_settings, "mode_opa_fail_closed", True)
                        )
                    except Exception:
                        fail_closed = True
                else:
                    fail_closed = True
                if fail_closed:
                    LOGGER.error("OPA evaluation error (fail-closed deny): %s", exc)
                    app_metrics.OPA_DENY_TOTAL.inc()
                    return Response(
                        content=json.dumps({"detail": "OPA policy unavailable"}),
                        status_code=403,
                        media_type="application/json",
                    )
                LOGGER.debug("OPA evaluation error (fallback allow): %s", exc)
                app_metrics.OPA_ALLOW_TOTAL.inc()
                return await call_next(request)

        # OPA is configured – call external OPA service
        policy_path = _policy_path_for_mode()
        query_url = f"{opa_url.rstrip('/')}/v1/data/{policy_path}"
        try:
            import httpx

            timeout_seconds = 2.0
            if shared_settings is not None:
                try:
                    timeout_seconds = float(
                        getattr(shared_settings, "opa_timeout_seconds", 2.0)
                    )
                except Exception:
                    timeout_seconds = 2.0
            async with httpx.AsyncClient(timeout=timeout_seconds) as client:
                resp = await client.post(query_url, json={"input": input_payload})
            if resp.status_code == 200:
                result = resp.json().get("result", {})
                # Accept both object {allow: bool} and primitive boolean responses
                if isinstance(result, dict):
                    allowed = bool(result.get("allow", True))
                else:
                    allowed = bool(result)
                if not allowed:
                    # Emit OPA deny metric
                    app_metrics.OPA_DENY_TOTAL.inc()
                    # Return HTTP 403
                    return Response(
                        content=json.dumps({"detail": "OPA policy denied request"}),
                        status_code=403,
                        media_type="application/json",
                    )
                else:
                    app_metrics.OPA_ALLOW_TOTAL.inc()
            else:
                LOGGER.debug("OPA returned unexpected status %s", resp.status_code)
                # Treat unexpected status as a safe‑allow fallback
                app_metrics.OPA_ALLOW_TOTAL.inc()
        except Exception as exc:
            # Failure to contact OPA – strict fail-closed by default
            if shared_settings is not None:
                try:
                    fail_closed = bool(
                        getattr(shared_settings, "mode_opa_fail_closed", True)
                    )
                except Exception:
                    fail_closed = True
            else:
                fail_closed = True
            if fail_closed:
                LOGGER.error("OPA request failed (fail-closed deny): %s", exc)
                app_metrics.OPA_DENY_TOTAL.inc()
                return Response(
                    content=json.dumps({"detail": "OPA policy unavailable"}),
                    status_code=403,
                    media_type="application/json",
                )
            LOGGER.debug("OPA request failed (fallback allow): %s", exc)
            app_metrics.OPA_ALLOW_TOTAL.inc()
            # Continue processing the request instead of denying

        # If we reach here OPA allowed the request (or fallback allowed)
        return await call_next(request)


async def opa_enforcement(
    request: Request, call_next: Callable[[Request], Awaitable[Any]]
) -> Any:
    """FastAPI middleware that sends request data to OPA for allow/deny.

    The input payload includes:
    - ``path``: request URL path
    - ``method``: HTTP method
    - ``headers``: dict of request headers (lower‑cased keys)
    - ``query_params``: dict of query parameters
    - ``body``: JSON body if present, otherwise ``None``

    If OPA returns ``allow: false`` the request is aborted with ``403``.
    Errors contacting OPA result in a safe *allow* fallback (consistent with the
    ``OPAClient.evaluate`` implementation).
    """
    try:
        # Build a lightweight input for OPA – avoid reading large bodies.
        body = None
        if request.headers.get("content-type", "").startswith("application/json"):
            try:
                body = await request.json()
            except Exception:
                body = None
        input_payload = {
            "path": request.url.path,
            "method": request.method,
            "headers": {k.lower(): v for k, v in request.headers.items()},
            "query_params": dict(request.query_params),
            "body": body,
        }
        allowed = opa_client.evaluate(input_payload)
        if not allowed:
            # Increment deny counter and log
            app_metrics.OPA_DENY_TOTAL.inc()
            LOGGER.info("OPA denied request %s %s", request.method, request.url.path)
            # Return JSON response instead of raising HTTPException to avoid 500 errors in middleware chain
            return JSONResponse(
                status_code=403, content={"detail": "OPA policy denied request"}
            )
        else:
            # Increment allow counter
            app_metrics.OPA_ALLOW_TOTAL.inc()
    except HTTPException:
        raise
    except Exception as e:
        # Unexpected error – log and allow (defensive)
        LOGGER.warning("OPA middleware error, allowing request: %s", e)
    response = await call_next(request)
    return response
