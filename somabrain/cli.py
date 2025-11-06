"""
Command Line Interface Module for SomaBrain.

This module provides command-line interfaces for running the SomaBrain API server
and performing journal maintenance operations. It includes utilities for launching
the FastAPI application and managing persistent journals.

Key Features:
- FastAPI server launcher with configurable host/port
- Journal rotation and compaction utilities
- Environment variable support for configuration
- Argument parsing for CLI commands

Functions:
    run_api: Launch the FastAPI API server using uvicorn.
    journal_cli: Command-line interface for journal maintenance operations.
"""

from __future__ import annotations

import argparse
import os
import sys

from .config import get_config
# Journal subsystem removed: compact_journal / rotate_journal no longer available.


def run_api() -> None:
    """
    Launch the FastAPI API server via uvicorn.

    Console entry point for running the SomaBrain API server. Respects environment
    variables for host and port configuration, and loads SomaBrain configuration
    from standard sources.

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
        >>> # somabrain-api --host localhost --port 3000
        >>>
        >>> # Or set environment:
        >>> # export HOST=127.0.0.1
        >>> # export PORT=8080
        >>> # somabrain-api
    """
    try:
        import uvicorn  # type: ignore
    except Exception:
        print(
            "uvicorn is required to run the API (pip install uvicorn)", file=sys.stderr
        )
        raise
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run("somabrain.app:app", host=host, port=port, reload=False)


def journal_cli(argv: list[str] | None = None) -> int:  # legacy entrypoint retained
    raise SystemExit("Journal CLI removed (fail-fast architecture).")
