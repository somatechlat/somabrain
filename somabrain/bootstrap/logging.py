"""Cognitive logging setup for SomaBrain.

This module provides comprehensive logging configuration for brain-like
cognitive monitoring, including specialized loggers for different brain regions.

VIBE Compliance:
    - Uses DI container to track logging initialization state
    - Logger instances obtained via Python's logging module (standard pattern)
    - No module-level mutable state for logger references
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Tuple

from django.conf import settings


@dataclass
class LoggingState:
    """Tracks logging initialization state.

    VIBE Compliance:
        - Managed via DI container instead of module-level globals
        - Explicit state tracking for idempotent setup
    """

    initialized: bool = False


def _get_logging_state() -> LoggingState:
    """Get logging state from DI container."""
    from somabrain.core.container import container

    if not container.has("logging_state"):
        container.register("logging_state", LoggingState)
    return container.get("logging_state")


def setup_logging() -> None:
    """Setup comprehensive logging for cognitive brain monitoring.

    Initializes loggers for:
    - General system events
    - Cognitive processing
    - Error handling

    Log output is sent to both console and 'somabrain.log'.

    VIBE Compliance:
        - Uses DI container to track initialization state
        - Idempotent - safe to call multiple times
    """
    state = _get_logging_state()
    if state.initialized:
        return

    root = logging.getLogger()
    already_configured = bool(getattr(root, "handlers", None))

    if not already_configured:
        handlers: list[logging.Handler] = [logging.StreamHandler()]

        # Resolve a writable file path for logs under hardened containers
        # Priority: SOMABRAIN_LOG_PATH > /app/logs/somabrain.log > CWD/somabrain.log
        # Use centralized Settings for log path
        log_path = settings.log_path
        candidate = log_path
        try:
            if not os.path.isabs(candidate):
                if os.path.isdir("/app/logs"):
                    candidate = os.path.join("/app/logs", candidate)
                else:
                    candidate = os.path.join(os.getcwd(), candidate)
            parent = os.path.dirname(candidate) or "."
            if parent and not os.path.exists(parent):
                # Best-effort; on read-only rootfs this may fail, which is fine
                os.makedirs(parent, exist_ok=True)
            # Try to attach a file handler; fall back to stdout-only if not writable
            handlers.append(logging.FileHandler(candidate, mode="a"))
        except Exception:
            # File logging not available (likely read-only FS). Continue with stream only.
            pass

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=handlers,
        )

    # Create specialized loggers for different brain regions
    logger = logging.getLogger("somabrain")
    cognitive_logger = logging.getLogger("somabrain.cognitive")
    error_logger = logging.getLogger("somabrain.errors")

    # Set levels
    cognitive_logger.setLevel(logging.DEBUG)
    error_logger.setLevel(logging.ERROR)

    # Add cognitive-specific formatting when we own the handler stack
    if not any(
        isinstance(h, logging.StreamHandler) and getattr(h, "_somabrain_marker", False)
        for h in cognitive_logger.handlers
    ):
        cognitive_handler = logging.StreamHandler()
        cognitive_handler.setFormatter(
            logging.Formatter("%(asctime)s - COGNITIVE - %(levelname)s - %(message)s")
        )
        setattr(cognitive_handler, "_somabrain_marker", True)
        cognitive_logger.addHandler(cognitive_handler)

    state.initialized = True
    logger.info("🧠 SomaBrain cognitive logging initialized")


def get_loggers() -> Tuple[logging.Logger, logging.Logger, logging.Logger]:
    """Get the configured loggers.

    Returns:
        Tuple of (logger, cognitive_logger, error_logger)

    VIBE Compliance:
        - Uses Python's logging module directly (standard pattern)
        - No module-level mutable state
    """
    return (
        logging.getLogger("somabrain"),
        logging.getLogger("somabrain.cognitive"),
        logging.getLogger("somabrain.errors"),
    )


def get_logger() -> logging.Logger:
    """Get the main somabrain logger.

    VIBE Compliance:
        - Uses Python's logging module directly
    """
    return logging.getLogger("somabrain")


def get_cognitive_logger() -> logging.Logger:
    """Get the cognitive processing logger.

    VIBE Compliance:
        - Uses Python's logging module directly
    """
    return logging.getLogger("somabrain.cognitive")


def get_error_logger() -> logging.Logger:
    """Get the error logger.

    VIBE Compliance:
        - Uses Python's logging module directly
    """
    return logging.getLogger("somabrain.errors")
