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
from .journal import compact_journal, rotate_journal


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


def journal_cli(argv: list[str] | None = None) -> int:
    """
    Command-line interface for journal maintenance operations.

    Provides CLI commands for rotating and compacting SomaBrain journals.
    Supports namespace-specific operations and configurable parameters.

    Commands:
        rotate: Rotate journal files when they exceed size limits
        compact: Compact journal files to reduce storage

    Args:
        argv (list[str] | None, optional): Command line arguments. Defaults to sys.argv.

    Returns:
        int: Exit code (0 for success, 1 for failure).

    Examples:
        >>> # Rotate journal with custom settings
        >>> journal_cli(["rotate", "--namespace", "test", "--max-bytes", "5000000", "--keep", "5"])
        >>>
        >>> # Compact journal for specific namespace
        >>> journal_cli(["compact", "--namespace", "production"])
        >>>
        >>> # From command line:
        >>> # somabrain-journal rotate --max-bytes 10000000
        >>> # somabrain-journal compact --namespace my-namespace
    """
    parser = argparse.ArgumentParser(
        prog="somabrain-journal", description="Journal maintenance"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_rot = sub.add_parser("rotate")
    p_rot.add_argument("--namespace", default="public")
    p_rot.add_argument("--max-bytes", type=int, default=10_000_000)
    p_rot.add_argument("--keep", type=int, default=3)
    p_cmp = sub.add_parser("compact")
    p_cmp.add_argument("--namespace", default="public")
    args = parser.parse_args(argv)

    cfg = get_config()
    base_dir = str(getattr(cfg, "journal_dir", "./data/somabrain"))
    ns = str(getattr(args, "namespace", "public"))
    if args.cmd == "rotate":
        rot = rotate_journal(
            base_dir,
            ns,
            max_bytes=int(getattr(args, "max_bytes", 10_000_000)),
            keep=int(getattr(args, "keep", 3)),
        )
        print(rot if rot else "no-rotate")
        return 0
    if args.cmd == "compact":
        ok = compact_journal(base_dir, ns)
        print("ok" if ok else "fail")
        return 0 if ok else 1
    return 1
