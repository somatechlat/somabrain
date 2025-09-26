"""
Controls Middleware Module for SomaBrain

This module implements FastAPI middleware for request control, policy enforcement,
and audit logging. It provides security controls, provenance verification, and
operational monitoring for the SomaBrain API.

Key Features:
- Policy-based request filtering and control
- HMAC-based provenance verification for write operations
- Comprehensive audit logging
- Request body capture and restoration
- Client identification and tracking
- Configurable strict mode for security

Security Controls:
- Policy engine evaluation for each request
- Provenance validation using HMAC-SHA256
- Request denial with appropriate HTTP status codes
- Audit trail for compliance and debugging

Integration:
- FastAPI BaseHTTPMiddleware for seamless integration
- Policy engine for configurable rules
- Audit logger for persistent event tracking
- Metrics collection for monitoring

Classes:
    ControlsMiddleware: Main middleware implementation

Functions:
    None (middleware-based implementation)
"""

from __future__ import annotations

from typing import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..config import load_config
from .audit import AuditLogger
from .metrics import POLICY_DECISIONS
from .policy import PolicyEngine
from .provenance import verify_hmac_sha256


class ControlsMiddleware(BaseHTTPMiddleware):
    def __init__(
        self, app, engine: PolicyEngine | None = None, audit: AuditLogger | None = None
    ):
        super().__init__(app)
        self.engine = engine or PolicyEngine()
        self.audit = audit or AuditLogger()

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ):
        raw_body = b""
        try:
            if request.method.upper() in ("POST", "PUT", "PATCH"):
                raw_body = await request.body()
                # restore for downstream handlers
                request._body = raw_body  # type: ignore[attr-defined]
        except Exception:
            raw_body = b""
        headers = dict(request.headers)
        # Load fresh configuration for this request
        cfg = load_config()
        ctx = {
            "path": request.url.path,
            "method": request.method,
            "headers": headers,
            "client": getattr(request.client, "host", None),
            "user_agent": headers.get("user-agent", ""),
            "content_type": headers.get("content-type", ""),
            "body_size": len(raw_body or b""),
            "provenance_valid": None,
            "provenance_strict": bool(cfg.provenance_strict_deny),
            "require_provenance": bool(cfg.require_provenance),
        }
        # Optional provenance HMAC validation for write-like paths
        if (
            cfg.require_provenance
            and request.method.upper() == "POST"
            and (
                str(ctx.get("path", "")).startswith("/remember")
                or str(ctx.get("path", "")).startswith("/act")
            )
        ):
            # mypy: headers may contain atypical types; coerce to str safely
            header_val = (
                headers.get("X-Provenance") or headers.get("x-provenance") or ""
            )
            header_str = str(header_val)
            try:
                ctx["provenance_valid"] = verify_hmac_sha256(
                    cfg.provenance_secret, raw_body, header_str  # type: ignore[arg-type]
                )
            except Exception:
                ctx["provenance_valid"] = None

        # Compatibility guard: common mistake where clients send a list of chat turns to /remember
        # Provide a clear error before Pydantic's 422 to reduce log noise and guide integration.
        try:
            if (
                request.method.upper() == "POST"
                and str(ctx.get("path", ""))[:9] == "/remember"
            ):
                b = (raw_body or b"").lstrip()
                # tolerate UTF-8 BOM
                if b.startswith(b"\xef\xbb\xbf"):
                    b = b[3:]
                if b[:1] == b"[":
                    return JSONResponse(
                        status_code=400,
                        content={
                            "error": "Invalid body for /remember: expected JSON object, received array",
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
                                        "endpoint": "/remember",
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
                    )
        except Exception:
            # best-effort guard; fall through to normal handling
            pass
        dec = self.engine.evaluate(ctx)
        try:
            POLICY_DECISIONS.labels(decision=dec.decision).inc()
        except Exception:
            pass
        # Audit pre decision
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
            return Response(status_code=503, content=b"policy deny")
        resp = await call_next(request)
        # Audit post response
        self.audit.write(
            {
                "phase": "post",
                "status": getattr(resp, "status_code", 0),
                "path": ctx["path"],
                "client": ctx.get("client"),
            }
        )
        # Tag review decision in header
        if dec.decision == "review":
            resp.headers["X-Policy-Review"] = "true"
        return resp
