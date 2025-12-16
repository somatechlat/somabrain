"""Cognitive Middleware - Request processing and monitoring."""

from __future__ import annotations

import logging
import time

from fastapi import HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger("somabrain.cognitive")


class CognitiveErrorHandler:
    """Advanced error handling for brain-like cognitive processing."""

    @staticmethod
    def handle_error(
        error: Exception, context: str = "", request_id: str | None = None
    ) -> dict:
        """Handle errors with brain-like analysis and recovery suggestions."""
        import traceback

        error_info = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "timestamp": time.time(),
            "request_id": request_id,
            "traceback": traceback.format_exc(),
            "recovery_suggestions": [],
        }

        if isinstance(error, HTTPException):
            error_info["recovery_suggestions"] = [
                "Check request parameters",
                "Verify authentication",
            ]
        elif "embedding" in str(error).lower():
            error_info["recovery_suggestions"] = [
                "Check embedding service",
                "Alternative simpler embeddings",
            ]
        elif "memory" in str(error).lower():
            error_info["recovery_suggestions"] = [
                "Check external memory backend",
                "Verify SOMABRAIN_MEMORY_HTTP_ENDPOINT",
            ]
        elif "rate" in str(error).lower():
            error_info["recovery_suggestions"] = [
                "Implement backoff strategy",
                "Check rate limits",
            ]
        else:
            error_info["recovery_suggestions"] = [
                "Log for analysis",
                "Implement graceful degradation",
            ]

        logger.error(f"Cognitive Error in {context}: {error_info}")
        return error_info


class CognitiveMiddleware:
    """Middleware for brain-like request processing and monitoring."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = f"{time.time()}_{hash(str(scope))}"
        path = scope.get("path", "")
        method = scope.get("method", "")
        start_time = time.time()

        logger.info(
            f"🧠 Request {request_id}: {method} {path} - Cognitive processing initiated"
        )

        try:
            await self.app(scope, receive, send)
            processing_time = time.time() - start_time
            logger.info(
                f"🧠 Request {request_id}: {method} {path} - Processing completed in {processing_time:.4f}s"
            )

        except HTTPException:
            raise
        except Exception as e:
            processing_time = time.time() - start_time
            error_info = CognitiveErrorHandler.handle_error(
                e, f"{method} {path}", request_id
            )

            error_response = JSONResponse(
                status_code=500,
                content={
                    "error": "Cognitive processing error",
                    "request_id": request_id,
                    "recovery_suggestions": error_info["recovery_suggestions"],
                },
            )
            await error_response(scope, receive, send)
            logger.error(
                f"🧠 Request {request_id}: {method} {path} - Error after {processing_time:.4f}s: {str(e)}"
            )
            return

        logger.debug(f"✅ Request {request_id} completed successfully")
