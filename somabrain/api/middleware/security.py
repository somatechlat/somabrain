"""Security Middleware - Request security filtering."""

from __future__ import annotations

import logging
import re

from fastapi.responses import JSONResponse

logger = logging.getLogger("somabrain.cognitive")


class SecurityMiddleware:
    """Advanced security middleware for brain protection."""

    def __init__(self, app):
        self.app = app
        self.suspicious_patterns = [
            re.compile(r"union\s+select", re.IGNORECASE),
            re.compile(r";\s*drop", re.IGNORECASE),
            re.compile(r"<script", re.IGNORECASE),
            re.compile(r"eval\s*\(", re.IGNORECASE),
        ]

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = scope.get("method", "")
        headers = dict(scope.get("headers", []))

        if self._is_suspicious_request(path, method, headers):
            logger.warning(f"🚨 Suspicious request blocked: {method} {path}")
            response = JSONResponse(
                status_code=403,
                content={"error": "Request blocked for security reasons"},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)

    def _is_suspicious_request(self, path: str, method: str, headers: dict) -> bool:
        """Analyze request for suspicious patterns."""
        for pattern in self.suspicious_patterns:
            if pattern.search(path):
                return True
        return False

