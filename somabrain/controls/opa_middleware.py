"""
OPA Middleware Module for SomaBrain (Django Version)

Migrated from somabrain/api/middleware/opa.py.
Forwards request data to an OPA side-car for policy enforcement.
"""

from __future__ import annotations

import json
import logging
import httpx
from typing import Any, Callable

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.conf import settings

from somabrain import metrics as app_metrics
from somabrain.opa.client import opa_client, _policy_path_for_mode

LOGGER = logging.getLogger("somabrain.controls.opa")


class SimpleOPAEngine:
    """Lightweight wrapper around the OPA HTTP endpoint for health checks.

    This class stores the base URL and offers an async ``health`` method used by the
    health endpoint to verify that the OPA service is reachable.
    """

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def health_sync(self) -> bool:
        """Return True if the OPA /health endpoint responds with 200 (Sync)."""
        try:
            with httpx.Client(timeout=2.0) as client:
                resp = client.get(f"{self.base_url}/health")
                return resp.status_code == 200
        except Exception:
            return False

    async def health(self) -> bool:
        """Return True if the OPA /health endpoint responds with 200."""
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(f"{self.base_url}/health")
                return resp.status_code == 200
        except Exception:
            return False


class OpaMiddleware:
    """Django Middleware for OPA Enforcment."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        try:
            opa_url = getattr(settings, "SOMABRAIN_OPA_URL", None)
        except Exception:
            opa_url = None

        input_payload: dict[str, Any] = {
            "method": request.method,
            "path": request.path,
        }

        # Try to read JSON body
        # Django request.body is bytes. Accessing it is safe if downstream uses request.body or DRF/Ninja.
        try:
            body_bytes = request.body
            if body_bytes:
                try:
                    input_payload["json"] = json.loads(body_bytes)
                except Exception:
                    input_payload["raw_body"] = body_bytes.decode(errors="ignore")
        except Exception:
            pass

        # If OPA URL is not configured, fall back to local opa_client evaluation
        if not opa_url:
            try:
                allowed = opa_client.evaluate(input_payload)
                if not allowed:
                    app_metrics.OPA_DENY_TOTAL.inc()
                    return JsonResponse({"detail": "OPA policy denied request"}, status=403)
                else:
                    app_metrics.OPA_ALLOW_TOTAL.inc()
                    return self.get_response(request)
            except Exception as exc:
                LOGGER.error("OPA evaluation error (fail-closed deny): %s", exc)
                app_metrics.OPA_DENY_TOTAL.inc()
                return JsonResponse({"detail": "OPA policy unavailable"}, status=403)

        # OPA is configured – call external OPA service (Sync for Django Middleware)
        policy_path = _policy_path_for_mode()
        query_url = f"{opa_url.rstrip('/')}/v1/data/{policy_path}"
        
        try:
            timeout_seconds = float(getattr(settings, "SOMABRAIN_OPA_TIMEOUT", 2.0))
            with httpx.Client(timeout=timeout_seconds) as client:
                resp = client.post(query_url, json={"input": input_payload})
            
            if resp.status_code == 200:
                result = resp.json().get("result", {})
                if isinstance(result, dict):
                    allowed = bool(result.get("allow", True))
                else:
                    allowed = bool(result)
                
                if not allowed:
                    app_metrics.OPA_DENY_TOTAL.inc()
                    return JsonResponse({"detail": "OPA policy denied request"}, status=403)
                else:
                    app_metrics.OPA_ALLOW_TOTAL.inc()
            else:
                LOGGER.error("OPA returned unexpected status %s", resp.status_code)
                app_metrics.OPA_DENY_TOTAL.inc()
                return JsonResponse({"detail": "OPA policy service error"}, status=403)

        except Exception as exc:
            LOGGER.error("OPA request failed (fail-closed deny): %s", exc)
            app_metrics.OPA_DENY_TOTAL.inc()
            return JsonResponse({"detail": "OPA policy unavailable"}, status=403)

        return self.get_response(request)
