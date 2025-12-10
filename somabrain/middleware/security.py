"""Security middleware for brain protection.

This module provides security middleware that blocks suspicious requests
and patterns to protect the cognitive API.
"""

from __future__ import annotations

import logging
import re

from fastapi.responses import JSONResponse

_log = logging.getLogger(__name__)
_cognitive_log = logging.getLogger("somabrain.cognitive")


class SecurityMiddleware:
    """Advanced security middleware for brain protection.

    Blocks suspicious requests and patterns to protect the cognitive API.
    """

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

        # Extract request info for security analysis
        path = scope.get("path", "")
        method = scope.get("method", "")
        headers = dict(scope.get("headers", []))

        # Security checks
        if self._is_suspicious_request(path, method, headers):
            _cognitive_log.warning(
                "🚨 Suspicious request blocked: %s %s", method, path
            )
            response = JSONResponse(
                status_code=403,
                content={"error": "Request blocked for security reasons"},
            )
            await response(scope, receive, send)
            return

        await self.app(scope, receive, send)

    def _is_suspicious_request(self, path: str, method: str, headers: dict) -> bool:
        """Analyze request for suspicious patterns."""
        # Check path for suspicious patterns
        for pattern in self.suspicious_patterns:
            if pattern.search(path):
                return True

        # Check for unusual headers
        suspicious_headers = ["x-forwarded-for", "x-real-ip"]
        for header in suspicious_headers:
            if header in headers:
                # Additional validation could be added here
                pass

        return False
