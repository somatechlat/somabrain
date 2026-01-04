"""Module __init__."""

from common.logging import logger  # noqa: F401

"""
Memory package import gate.

This repository MUST use a real memory backend. Importing ``memory`` without
installing/providing the real client raises immediately to prevent silent
fallbacks or placeholder behavior.
"""

raise ImportError(
    "The real memory backend is required. Install/provide the memory client package "
    "or mount it into the image. No fallback implementations are permitted."
)
