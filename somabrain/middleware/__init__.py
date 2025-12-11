"""Middleware components for SomaBrain cognitive API.

This package contains middleware classes for request processing, security,
error handling, and input validation.
"""

from somabrain.middleware.cognitive import CognitiveMiddleware
from somabrain.middleware.security import SecurityMiddleware
from somabrain.middleware.error_handler import CognitiveErrorHandler
from somabrain.middleware.validation import CognitiveInputValidator
from somabrain.middleware.validation_handler import handle_validation_error

__all__ = [
    "CognitiveMiddleware",
    "SecurityMiddleware",
    "CognitiveErrorHandler",
    "CognitiveInputValidator",
    "handle_validation_error",
]
