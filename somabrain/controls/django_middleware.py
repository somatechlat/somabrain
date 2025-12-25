"""
Controls Middleware Module for SomaBrain (Django Version)

Migrated from somabrain/controls/middleware.py.
Implements security controls, policy enforcement, and audit logging.
"""

from __future__ import annotations

import logging
from typing import Callable, Any

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.conf import settings

from somabrain.controls.audit import AuditLogger
from somabrain.controls.metrics import POLICY_DECISIONS
from somabrain.controls.policy import PolicyEngine
from somabrain.controls.provenance import verify_hmac_sha256


class ControlsMiddleware:
    """Django Middleware for SomaBrain Controls."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response
        self.engine = PolicyEngine()
        self.audit = AuditLogger()
        self.logger = logging.getLogger("somabrain.controls.middleware")

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Pre-process request
        
        # Read body safely (Django caches it)
        raw_body = b""
        try:
            if request.method in ("POST", "PUT", "PATCH"):
                raw_body = request.body
        except Exception:
            raw_body = b""

        # Build context
        headers = dict(request.headers)
        # Normalize headers to lower case keys for consistency
        normalized_headers = {k.lower(): v for k, v in headers.items()}
        
        # Extract client IP
        if x_forwarded := normalized_headers.get("x-forwarded-for"):
            client_ip = x_forwarded.split(",")[0].strip()
        else:
            client_ip = request.META.get("REMOTE_ADDR")

        ctx: dict[str, Any] = {
            "path": request.path,
            "method": request.method,
            "headers": normalized_headers,
            "client": client_ip,
            "user_agent": normalized_headers.get("user-agent", ""),
            "content_type": normalized_headers.get("content-type", ""),
            "body_size": len(raw_body),
            "provenance_valid": None,
            "provenance_strict": bool(getattr(settings, "SOMABRAIN_PROVENANCE_STRICT_DENY", False)),
            "require_provenance": bool(getattr(settings, "SOMABRAIN_REQUIRE_PROVENANCE", False)),
        }

        # Provenance Check
        if (
            ctx["require_provenance"]
            and request.method == "POST"
            and (
                ctx["path"].startswith("/memory/remember")
                or ctx["path"].startswith("/act")
            )
        ):
            header_val = normalized_headers.get("x-provenance", "")
            try:
                secret = getattr(settings, "SOMABRAIN_PROVENANCE_SECRET", "")
                ctx["provenance_valid"] = verify_hmac_sha256(
                    secret,
                    raw_body,
                    str(header_val),
                )
            except Exception:
                ctx["provenance_valid"] = None

        # Compatibility guard for /memory/remember array input
        try:
            if request.method == "POST" and ctx["path"].startswith("/memory/remember"):
                b = raw_body.lstrip()
                if b.startswith(b"\xef\xbb\xbf"):
                    b = b[3:]
                if b[:1] == b"[":
                    return JsonResponse(
                        {
                            "error": "Invalid body for /memory/remember: expected JSON object, received array",
                            "hint": {
                                "expected": {
                                    "coord": "optional string",
                                    "payload": {
                                        "task": "string",
                                        "importance": 1,
                                        "memory_type": "episodic",
                                    },
                                },
                                "alternatives": [
                                    {
                                        "endpoint": "/memory/remember",
                                        "body": {
                                            "payload": {
                                                "task": "...",
                                                "memory_type": "semantic",
                                            }
                                        },
                                    }
                                ],
                            },
                        },
                        status=400,
                    )
        except Exception as exc:
            self.logger.exception("Compatibility guard failed: %s", exc)

        # Policy Evaluation
        dec = self.engine.evaluate(ctx)
        try:
            POLICY_DECISIONS.labels(decision=dec.decision).inc()
        except Exception:
            pass

        # Audit Pre
        self.audit.write(
            {
                "phase": "pre",
                "decision": dec.decision,
                "reason": dec.reason,
                "path": ctx["path"],
                "method": ctx["method"],
                "client": ctx.get("client"),
                "ua": ctx.get("user_agent"),
                "ct": ctx.get("content_type"),
                "blen": ctx.get("body_size"),
            }
        )

        if dec.decision == "deny":
            return HttpResponse(b"policy deny", status=503)

        # Process Request
        response = self.get_response(request)

        # Audit Post
        self.audit.write(
            {
                "phase": "post",
                "status": response.status_code,
                "path": ctx["path"],
                "client": ctx.get("client"),
            }
        )

        # Add headers
        if dec.decision == "review":
            response["X-Policy-Review"] = "true"

        return response
