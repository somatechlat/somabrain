"""
Command Line Interface Module for SomaBrain.

Provides the console entry point for running the SomaBrain API server.
All former journal maintenance commands have been removed under the
strict fail-fast architecture (no local persistence alternatives).

Functions:
    run_api: Launch the FastAPI API server using uvicorn.
"""

from __future__ import annotations

import sys

# Direct import of the shared settings object.
from common.config.settings import settings


def get_config():
    """Compatibility wrapper returning the shared settings.

    Returns the ``settings`` instance for configuration access.
    """
    return settings


# Journal subsystem removed: compact_journal / rotate_journal no longer available.


def run_api() -> None:
    """
    Launch the FastAPI API server via uvicorn.

    Console entry point for running the SomaBrain API server. Uses centralized
    Settings for host and port configuration.

    Usage:
        somabrain-api

    Environment Variables:
        HOST: Server host (default: "0.0.0.0") - via settings.cli_host
        PORT: Server port (default: 8000) - via settings.cli_port
        SOMABRAIN_*: Configuration overrides

    Raises:
        Exception: If uvicorn is not installed or server fails to start.

    Example:
        >>> # Set environment:
        >>> # export HOST=127.0.0.1
        >>> # export PORT=8080
        >>> # somabrain-api
    """
    try:
        import uvicorn
    except Exception:
        print(
            "uvicorn is required to run the API (pip install uvicorn)", file=sys.stderr
        )
        raise
    # Use centralized Settings for HOST/PORT configuration
    host = settings.cli_host
    port = settings.cli_port
    uvicorn.run("somabrain.app:app", host=host, port=port, reload=False)


def journal_cli() -> int:  # retained only to fail fast if invoked
    raise SystemExit("Journal CLI removed (fail-fast architecture).")
