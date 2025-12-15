"""Cognitive middleware for brain-like request processing.

This module provides middleware for request lifecycle logging, error handling,
and processing time tracking.
"""

from __future__ import annotations

import logging
import time

from fastapi import HTTPException
from fastapi.responses import JSONResponse

from somabrain.middleware.error_handler import CognitiveErrorHandler

_log = logging.getLogger(__name__)
_cognitive_log = logging.getLogger("somabrain.cognitive")


class CognitiveMiddleware:
    """Middleware for brain-like request processing and monitoring.

    Logs request lifecycle, handles errors, and tracks processing time for each API call.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Extract request info
        request_id = f"{time.time()}_{hash(str(scope))}"
        path = scope.get("path", "")
        method = scope.get("method", "")

        start_time = time.time()

        # Log cognitive request initiation
        _cognitive_log.info(
            "🧠 Request %s: %s %s - Cognitive processing initiated",
            request_id,
            method,
            path,
        )

        # Process request with error handling
        try:
            await self.app(scope, receive, send)
            processing_time = time.time() - start_time

            _cognitive_log.info(
                "🧠 Request %s: %s %s - Processing completed in %.4fs",
                request_id,
                method,
                path,
                processing_time,
            )

        except HTTPException:
            # Allow FastAPI/Starlette to handle intentional HTTP errors (e.g. auth/validation).
            raise
        except Exception as e:
            processing_time = time.time() - start_time
            error_info = CognitiveErrorHandler.handle_error(e, f"{method} {path}", request_id)

            # Send error response
            error_response = JSONResponse(
                status_code=500,
                content={
                    "error": "Cognitive processing error",
                    "request_id": request_id,
                    "recovery_suggestions": error_info["recovery_suggestions"],
                },
            )

            await error_response(scope, receive, send)

            _cognitive_log.error(
                "🧠 Request %s: %s %s - Error after %.4fs: %s",
                request_id,
                method,
                path,
                processing_time,
                str(e),
            )
            return

        # Log successful completion
        _cognitive_log.debug("✅ Request %s completed successfully", request_id)
