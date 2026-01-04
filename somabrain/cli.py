"""
Command Line Interface Module for SomaBrain.

Provides the console entry point for running the SomaBrain Django server.
VIBE COMPLIANT: Pure Django - no uvicorn, no FastAPI.

Functions:
    run_server: Launch the Django development server.
"""

from __future__ import annotations

import os


def run_server() -> None:
    """
    Launch the Django development server.

    Console entry point for running the SomaBrain API server.
    Uses Django's built-in runserver command.

    Usage:
        somabrain-server

    Environment Variables:
        DJANGO_SETTINGS_MODULE: Settings module (default: somabrain.settings)
        HOST: Server host (default: "0.0.0.0")
        PORT: Server port (default: 9696)

    Example:
        >>> # Run on default port:
        >>> # somabrain-server
        >>> # Or with custom port:
        >>> # PORT=8000 somabrain-server
    """
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "somabrain.settings")

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

    host = os.environ.get("HOST", "0.0.0.0")
    port = os.environ.get("PORT", "9696")

    execute_from_command_line(["manage.py", "runserver", f"{host}:{port}"])
