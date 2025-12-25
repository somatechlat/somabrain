"""
Security Middleware - Request security filtering (Django Version).
"""

from __future__ import annotations

import logging
import re
from typing import Callable

from django.http import HttpRequest, HttpResponse, JsonResponse

logger = logging.getLogger("somabrain.cognitive")


class SecurityMiddleware:
    """Advanced security middleware for brain protection."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response
        self.suspicious_patterns = [
            re.compile(r"union\s+select", re.IGNORECASE),
            re.compile(r";\s*drop", re.IGNORECASE),
            re.compile(r"<script", re.IGNORECASE),
            re.compile(r"eval\s*\(", re.IGNORECASE),
        ]

    def __call__(self, request: HttpRequest) -> HttpResponse:
        path = request.path
        method = request.method
        # Django headers can be accessed via request.headers (case insensitive)
        # But for iteration/search we might want dict
        
        if self._is_suspicious_request(path, method, request.headers):
            logger.warning(f"🚨 Suspicious request blocked: {method} {path}")
            return JsonResponse(
                {"error": "Request blocked for security reasons"},
                status=403,
            )

        return self.get_response(request)

    def _is_suspicious_request(self, path: str, method: str, headers: Any) -> bool:
        """Analyze request for suspicious patterns."""
        for pattern in self.suspicious_patterns:
            if pattern.search(path):
                return True
        return False
