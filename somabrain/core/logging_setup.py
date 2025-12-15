"""Logging Setup - Cognitive brain monitoring logging configuration."""

from __future__ import annotations

import logging
import os

from common.config.settings import settings

# Global loggers
logger = None
cognitive_logger = None
error_logger = None


def setup_logging():
    """Setup comprehensive logging for cognitive brain monitoring."""
    global logger, cognitive_logger, error_logger

    root = logging.getLogger()
    already_configured = bool(getattr(root, "handlers", None))

    if not already_configured:
        handlers: list[logging.Handler] = [logging.StreamHandler()]

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
                os.makedirs(parent, exist_ok=True)
            handlers.append(logging.FileHandler(candidate, mode="a"))
        except Exception:
            pass

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=handlers,
        )

    logger = logging.getLogger("somabrain")
    cognitive_logger = logging.getLogger("somabrain.cognitive")
    error_logger = logging.getLogger("somabrain.errors")

    cognitive_logger.setLevel(logging.DEBUG)
    error_logger.setLevel(logging.ERROR)

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

    logger.info("🧠 SomaBrain cognitive logging initialized")
