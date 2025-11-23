import json
import logging
from typing import Any, Awaitable, Callable

from fastapi import HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

import somabrain.metrics as app_metrics
from somabrain.opa.client import opa_client, _policy_path_for_mode

# Import shared configuration; let import errors propagate if settings module is unavailable.
from common.config.settings import settings

LOGGER = logging.getLogger("somabrain.api.middleware.opa")


class OpaMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware that forwards request data to an OPA side‑car for policy enforcement.

    The middleware expects the environment variable ``SOMA_OPA_URL`` to contain the base URL
    of the OPA HTTP server (e.g. ``http://127.0.0.1:8181``). If the variable is not set, the
    middleware becomes a no‑op and all requests are allowed.
    """

    async def dispatch(self, request: Request, call_next):
        if settings is not None:
            try:
                opa_url = getattr(settings, "opa_url", None)
            except Exception:
                opa_url = None
        else:
            opa_url = None
        # No legacy fallback – rely solely on the canonical ``opa_url`` field.
        # If ``opa_url`` is empty, the middleware will treat OPA as unavailable.
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
                # Strict mode: always fail-closed when OPA evaluation fails
                LOGGER.error("OPA evaluation error (fail-closed deny): %s", exc)
                app_metrics.OPA_DENY_TOTAL.inc()
                return Response(
                    content=json.dumps({"detail": "OPA policy unavailable"}),
                    status_code=403,
                    media_type="application/json",
                )

        # OPA is configured – call external OPA service
        policy_path = _policy_path_for_mode()
        query_url = f"{opa_url.rstrip('/')}/v1/data/{policy_path}"
        try:
            import httpx

            timeout_seconds = 2.0
            if settings is not None:
                try:
                    timeout_seconds = float(
                        getattr(settings, "opa_timeout_seconds", 2.0)
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
                LOGGER.error("OPA returned unexpected status %s", resp.status_code)
                # Strict mode: fail-closed on unexpected status
                app_metrics.OPA_DENY_TOTAL.inc()
                return Response(
                    content=json.dumps({"detail": "OPA policy service error"}),
                    status_code=403,
                    media_type="application/json",
                )
        except Exception as exc:
            # Strict mode: always fail-closed when OPA is unreachable
            LOGGER.error("OPA request failed (fail-closed deny): %s", exc)
            app_metrics.OPA_DENY_TOTAL.inc()
            return Response(
                content=json.dumps({"detail": "OPA policy unavailable"}),
                status_code=403,
                media_type="application/json",
            )

        # If we reach here OPA allowed the request (or alternative allowed)
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
    Errors contacting OPA result in a safe *allow* alternative (consistent with the
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
        # Strict mode: fail-closed on unexpected middleware error
        LOGGER.error("OPA middleware error, denying request: %s", e)
        app_metrics.OPA_DENY_TOTAL.inc()
        return JSONResponse(status_code=403, content={"detail": "OPA middleware error"})
    response = await call_next(request)
    return response
