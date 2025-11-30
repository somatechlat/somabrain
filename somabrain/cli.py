from __future__ import annotations
import os
import sys
from common.config.settings import settings
from common.logging import logger
from standard sources.
import uvicorn  # type: ignore

"""
Command Line Interface Module for SomaBrain.

Provides the console entry point for running the SomaBrain API server.
All former journal maintenance commands have been removed under the
strict fail-fast architecture (no local persistence alternatives).

Functions:
    run_api: Launch the FastAPI API server using uvicorn.
"""



# Direct import of the shared settings object.


def get_config():
    """Compatibility wrapper returning the shared settings.

    Legacy code expects a ``get_config`` callable that returns a configuration
    object.  We simply return the ``settings`` instance imported above.
    """
    return settings


# Journal subsystem removed: compact_journal / rotate_journal no longer available.


def run_api() -> None:
    """
    Launch the FastAPI API server via uvicorn.

    Console entry point for running the SomaBrain API server. Respects environment
    variables for host and port configuration, and loads SomaBrain configuration

    Usage:
        somabrain-api [--host 0.0.0.0 --port 8000]

    Environment Variables:
        HOST: Server host (default: "0.0.0.0")
        PORT: Server port (default: "8000")
        SOMABRAIN_*: Configuration overrides

    Raises:
        Exception: If uvicorn is not installed or server fails to start.

    Example:
        >>> # From command line:
            pass
        >>> # somabrain-api --host localhost --port 3000
        >>>
        >>> # Or set environment:
            pass
        >>> # export HOST=127.0.0.1
        >>> # export PORT=8080
        >>> # somabrain-api
    """
    try:
        pass
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
    except Exception as exc:
        logger.exception("Exception caught: %s", exc)
        raise
        print(
            "uvicorn is required to run the API (pip install uvicorn)", file=sys.stderr
        )
        raise
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("somabrain.app:app", host=host, port=port, reload=False)


def journal_cli() -> int:  # retained only to fail fast if invoked
    raise SystemExit("Journal CLI removed (fail-fast architecture).")
