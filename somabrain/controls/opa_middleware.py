"""
OPA Middleware Module for SomaBrain (Django Version)

Migrated from somabrain/api/middleware/opa.py.
Forwards request data to an OPA side-car for policy enforcement.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from typing import Any

import httpx
from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse

from somabrain import metrics as app_metrics
from somabrain.opa.client import _policy_path_for_mode, opa_client

LOGGER = logging.getLogger("somabrain.controls.opa")

# Production accept path: OPA is authoritative but a per-request HTTP RTT
# cannot sit on a million-txn write. Positive decisions for the same
# (method, path, tenant, role) are reused for the configured window. Denies
# and errors are never cached (fail-closed). TTL is a settings key
# (OPA_ALLOW_TTL_S). Cache MUST be tenant-keyed — a cross-tenant reuse of an
# allow is a policy bypass (security review F-04).
_OPA_ALLOW_CACHE: dict[tuple[str, str, str, str], float] = {}
_OPA_HTTP: httpx.Client | None = None


def _opa_http(timeout: float) -> httpx.Client:
    global _OPA_HTTP
    if _OPA_HTTP is None or _OPA_HTTP.is_closed:
        _OPA_HTTP = httpx.Client(timeout=timeout)
    return _OPA_HTTP


class SimpleOPAEngine:
    """Lightweight wrapper around the OPA HTTP endpoint for health checks.

    This class stores the base URL and offers an async ``health`` method used by the
    health endpoint to verify that the OPA service is reachable.
    """

    def __init__(self, base_url: str):
        """Initialize the instance."""

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
        """Initialize the instance."""

        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Execute call  .

        Args:
            request: The request.
        """

        try:
            opa_url = getattr(settings, "SOMABRAIN_OPA_URL")
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
                    return JsonResponse(
                        {"detail": "OPA policy denied request"}, status=403
                    )
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
        # Tenant-keyed cache (F-04): never reuse an allow across principals.
        _auth = getattr(request, "auth", None) or {}
        _tenant = str(
            input_payload.get("tenant")
            or _auth.get("tenant_id")
            or _auth.get("tenant")
            or request.headers.get("X-Soma-Tenant")
            or ""
        )
        _role = str(_auth.get("role") or request.headers.get("X-Soma-Role") or "")
        cache_key = (str(request.method), str(request.path), _tenant, _role)
        now = time.monotonic()
        exp = _OPA_ALLOW_CACHE.get(cache_key)
        if exp is not None and exp > now:
            app_metrics.OPA_ALLOW_TOTAL.inc()
            return self.get_response(request)

        try:
            timeout_seconds = float(getattr(settings, "SOMABRAIN_OPA_TIMEOUT"))
            client = _opa_http(timeout_seconds)
            resp = client.post(query_url, json={"input": input_payload})

            if resp.status_code == 200:
                result = resp.json().get("result", {})
                if isinstance(result, dict):
                    # Fail-closed: only an explicit boolean True permits.
                    allowed = result.get("allow", False) is True
                else:
                    allowed = result is True

                if not allowed:
                    app_metrics.OPA_DENY_TOTAL.inc()
                    return JsonResponse(
                        {"detail": "OPA policy denied request"}, status=403
                    )
                else:
                    app_metrics.OPA_ALLOW_TOTAL.inc()
                    from somabrain.settings.resolve import require_setting

                    ttl = float(require_setting("OPA_ALLOW_TTL_S"))
                    if ttl > 0:
                        _OPA_ALLOW_CACHE[cache_key] = time.monotonic() + ttl
            else:
                LOGGER.error("OPA returned unexpected status %s", resp.status_code)
                app_metrics.OPA_DENY_TOTAL.inc()
                return JsonResponse({"detail": "OPA policy service error"}, status=403)

        except Exception as exc:
            LOGGER.error("OPA request failed (fail-closed deny): %s", exc)
            app_metrics.OPA_DENY_TOTAL.inc()
            return JsonResponse({"detail": "OPA policy unavailable"}, status=403)

        return self.get_response(request)
