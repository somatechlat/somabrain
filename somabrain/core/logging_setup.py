"""Logging Setup - Cognitive brain monitoring logging configuration.

VIBE Compliance:
    - Delegates to somabrain.bootstrap.logging for implementation
    - Logger instances obtained via Python's logging module (standard pattern)
    - No module-level mutable state for logger references

Note: This module delegates to somabrain.bootstrap.logging for the actual
implementation. It exists for backward compatibility with existing imports.
"""

from __future__ import annotations

import logging

from somabrain.bootstrap.logging import setup_logging

# Re-export for backward compatibility
__all__ = [
    "setup_logging",
    "logger",
    "cognitive_logger",
    "error_logger",
]


# Module-level logger references using Python's logging module directly
# These are not mutable state - they're just references to the logging hierarchy
logger = logging.getLogger("somabrain")
cognitive_logger = logging.getLogger("somabrain.cognitive")
error_logger = logging.getLogger("somabrain.errors")
