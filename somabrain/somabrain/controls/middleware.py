from __future__ import annotations

from typing import Callable, Awaitable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from .policy import PolicyEngine
from .audit import AuditLogger
from .metrics import POLICY_DECISIONS
from ..config import load_config
from .provenance import verify_hmac_sha256


class ControlsMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, engine: PolicyEngine | None = None, audit: AuditLogger | None = None):
        super().__init__(app)
        self.engine = engine or PolicyEngine()
        self.audit = audit or AuditLogger()
        self.cfg = load_config()

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]):
        raw_body = b""
        try:
            if request.method.upper() in ("POST", "PUT", "PATCH"):
                raw_body = await request.body()
                # restore for downstream handlers
                request._body = raw_body  # type: ignore[attr-defined]
        except Exception:
            raw_body = b""
        ctx = {
            "path": request.url.path,
            "method": request.method,
            "headers": dict(request.headers),
            "client": getattr(request.client, "host", None),
            "provenance_valid": None,
            "provenance_strict": bool(self.cfg.provenance_strict_deny),
        }
        # Optional provenance HMAC validation for write-like paths
        if self.cfg.require_provenance and request.method.upper() == "POST" and (ctx["path"].startswith("/remember") or ctx["path"].startswith("/act")):
            header = ctx["headers"].get("X-Provenance") or ctx["headers"].get("x-provenance") or ""
            ctx["provenance_valid"] = verify_hmac_sha256(self.cfg.provenance_secret, raw_body, header)
        dec = self.engine.evaluate(ctx)
        try:
            POLICY_DECISIONS.labels(decision=dec.decision).inc()
        except Exception:
            pass
        # Audit pre decision
        self.audit.write({"phase": "pre", "decision": dec.decision, "reason": dec.reason, "path": ctx["path"], "method": ctx["method"]})
        if dec.decision == "deny":
            return Response(status_code=503, content=b"policy deny")
        resp = await call_next(request)
        # Audit post response
        self.audit.write({"phase": "post", "status": getattr(resp, "status_code", 0), "path": ctx["path"]})
        # Tag review decision in header
        if dec.decision == "review":
            resp.headers["X-Policy-Review"] = "true"
        return resp
