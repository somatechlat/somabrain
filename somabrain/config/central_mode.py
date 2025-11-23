"""Centralized SomaBrain mode constants.

This module collapses legacy multi‑mode/dev abstractions into a single
enterprise mode constant. Dynamic/local override behaviours have been
removed to enforce a unified runtime configuration surface.
"""

ENTERPRISE_MODE = "enterprise"


def current_mode() -> str:
    """Return the active runtime mode (always enterprise)."""
    return ENTERPRISE_MODE
