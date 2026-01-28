"""SomaBrain ASGI application entry point (Django + Ninja)."""

import os

import django
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "somabrain.settings")
django.setup()

# Canonical ASGI app used by uvicorn/gunicorn
app = get_asgi_application()

# Useful re-exports for callers that previously imported from app.py
from somabrain.opa.engine import SimpleOPAEngine  # noqa: E402
from somabrain.scoring.memory import score_memory_candidate  # noqa: E402
from somabrain.middleware.cognitive import CognitiveErrorHandler  # noqa: E402
from somabrain.logging_config import setup_logging  # noqa: E402
