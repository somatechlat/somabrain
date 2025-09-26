"""Sphinx stub for somabrain.api.routers.link

This module provides lightweight signatures and docstrings for the
link router so autosummary can import it safely during documentation
builds. It intentionally avoids importing any runtime dependencies.
"""

from typing import Any, Dict


def post_link(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Accept a link payload and return an acknowledgement.

    This stub mirrors the public API surface of the real router handler.
    """
    return {"status": "stub", "received": True}


class LinkPayload:
    """Minimal data-holder type for documentation purposes."""

    def __init__(self, coord: str, metadata: Dict[str, Any] | None = None):
        self.coord = coord
        self.metadata = metadata or {}
