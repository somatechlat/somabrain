"""
Cognitive Middleware - Request processing and monitoring (Django Version).

Advanced error handling for brain-like cognitive processing.
"""

from __future__ import annotations

import logging
import time

from django.http import HttpRequest, HttpResponse, JsonResponse
from ninja.errors import HttpError
from .memory_client import memory_client
from .degradation import degradation_manager

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

        # Django Ninja uses HttpError, Django uses Http404 etc.
        # Check string representation or type if possible
        err_str = str(error).lower()

        if isinstance(error, HttpError):
            error_info["recovery_suggestions"] = [
                "Check request parameters",
                "Verify authentication",
            ]
        elif "embedding" in err_str:
            error_info["recovery_suggestions"] = [
                "Check embedding service",
                "Alternative simpler embeddings",
            ]
        elif "memory" in err_str:
            error_info["recovery_suggestions"] = [
                "Check external memory backend",
                "Verify SOMABRAIN_MEMORY_HTTP_ENDPOINT",
            ]
        elif "rate" in err_str:
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

    def __init__(self, get_response):
        """Initialize the instance."""

        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Execute call  .

        Args:
            request: The request.
        """

        request_id = f"{time.time()}_{id(request)}"
        path = request.path
        method = request.method
        start_time = time.time()

        logger.info(
            f"🧠 Request {request_id}: {method} {path} - Cognitive processing initiated"
        )

        try:
            response = self.get_response(request)

            # Check if response is an error response (4xx or 5xx) that wasn't raised
            if response.status_code >= 500:
                # It's already caught by Django ExceptionMiddleware?
                # Middleware only sees response if exception was handled or no exception raised.
                # If ExceptionMiddleware handles it, it returns response.
                # But we want to wrap UNHANDLED exceptions or analyze errors.
                pass

            processing_time = time.time() - start_time
            logger.info(
                f"🧠 Request {request_id}: {method} {path} - Processing completed in {processing_time:.4f}s"
            )
            return response

        except HttpError:
            raise
        except Exception as e:
            # Process exception (this catches exceptions that Django's ExceptionMiddleware hasn't caught yet if we place this outer)
            # Typically CognitiveMiddleware should be high up (outer).

            processing_time = time.time() - start_time
            error_info = CognitiveErrorHandler.handle_error(
                e, f"{method} {path}", request_id
            )

            logger.error(
                f"🧠 Request {request_id}: {method} {path} - Error after {processing_time:.4f}s: {str(e)}"
            )

            return JsonResponse(
                {
                    "error": "Cognitive processing error",
                    "request_id": request_id,
                    "recovery_suggestions": error_info["recovery_suggestions"],
                },
                status=500,
            )
