"""Cognitive logging setup for SomaBrain.

This module provides comprehensive logging configuration for brain-like
cognitive monitoring, including specialized loggers for different brain regions.
"""

from __future__ import annotations

import logging
import os
from typing import Tuple

from common.config.settings import settings

# Module-level logger references
_logger: logging.Logger | None = None
_cognitive_logger: logging.Logger | None = None
_error_logger: logging.Logger | None = None


def setup_logging() -> None:
    """Setup comprehensive logging for cognitive brain monitoring.

    Initializes loggers for:
    - General system events
    - Cognitive processing
    - Error handling

    Log output is sent to both console and 'somabrain.log'.
    """
    global _logger, _cognitive_logger, _error_logger

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
    _logger = logging.getLogger("somabrain")
    _cognitive_logger = logging.getLogger("somabrain.cognitive")
    _error_logger = logging.getLogger("somabrain.errors")

    # Set levels
    _cognitive_logger.setLevel(logging.DEBUG)
    _error_logger.setLevel(logging.ERROR)

    # Add cognitive-specific formatting when we own the handler stack
    if not any(
        isinstance(h, logging.StreamHandler) and getattr(h, "_somabrain_marker", False)
        for h in _cognitive_logger.handlers
    ):
        cognitive_handler = logging.StreamHandler()
        cognitive_handler.setFormatter(
            logging.Formatter("%(asctime)s - COGNITIVE - %(levelname)s - %(message)s")
        )
        setattr(cognitive_handler, "_somabrain_marker", True)
        _cognitive_logger.addHandler(cognitive_handler)

    _logger.info("🧠 SomaBrain cognitive logging initialized")


def get_loggers() -> Tuple[logging.Logger | None, logging.Logger | None, logging.Logger | None]:
    """Get the configured loggers.

    Returns:
        Tuple of (logger, cognitive_logger, error_logger)
    """
    return _logger, _cognitive_logger, _error_logger


def get_logger() -> logging.Logger | None:
    """Get the main somabrain logger."""
    return _logger


def get_cognitive_logger() -> logging.Logger | None:
    """Get the cognitive processing logger."""
    return _cognitive_logger


def get_error_logger() -> logging.Logger | None:
    """Get the error logger."""
    return _error_logger
