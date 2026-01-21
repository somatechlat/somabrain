"""SomaBrain Application Entry Point

DEPRECATED: FastAPI has been removed. This module provides backward
compatibility imports that redirect to Django Ninja API.

Migration completed: 2026-01-21
See: somabrain/_legacy/app_fastapi_deprecated.py for original code.
"""

import logging
import warnings

logger = logging.getLogger(__name__)

# Emit deprecation warning
warnings.warn(
    "somabrain.app is deprecated. Use somabrain.api.v1: or Django urls.py instead. "
    "FastAPI has been replaced with Django Ninja.",
    DeprecationWarning,
    stacklevel=2,
)

logger.warning(
    "⚠️ DEPRECATED: somabrain.app import detected. "
    "Migrate to Django Ninja (somabrain.api.v1) or Django views."
)


# Backward compatibility: Provide Django ASGI app as 'app'
import os

import django
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "somabrain.settings")
django.setup()

# The 'app' variable now points to Django ASGI application
app = get_asgi_application()

# Re-export commonly used items from the old app.py
# These have been extracted to proper Django modules:

# OPA Engine -> somabrain/opa/
try:
    from somabrain.opa.engine import SimpleOPAEngine
except ImportError:
    SimpleOPAEngine = None

# Scoring functions -> somabrain/scoring/
try:
    from somabrain.scoring.memory import score_memory_candidate
except ImportError:
    score_memory_candidate = None

# Error handler -> Django middleware
try:
    from somabrain.middleware.cognitive import CognitiveErrorHandler
except ImportError:
    CognitiveErrorHandler = None

# Logging setup -> somabrain/logging_config.py
try:
    from somabrain.logging_config import setup_logging
except ImportError:
    def setup_logging():
        """No-op for backward compatibility."""
        pass


def _deprecated_function(*args, **kwargs):
    """Placeholder for deprecated FastAPI endpoints."""
    raise NotImplementedError(
        "This function was part of FastAPI app.py and has been removed. "
        "Use Django Ninja API endpoints instead."
    )


# Mark all FastAPI-specific items as deprecated
recall = _deprecated_function
remember = _deprecated_function
health = _deprecated_function
