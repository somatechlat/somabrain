"""Sphinx stub for somabrain.api.routers.persona

Provides minimal signatures used by the documentation generator.
"""

from typing import Any, Dict


def get_persona(pid: str) -> Dict[str, Any]:
    """Return a persona by id (stub)."""
    return {"id": pid, "name": "stub-persona"}


def put_persona(pid: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Create or update a persona (stub)."""
    return {"id": pid, "updated": True}


def delete_persona(pid: str) -> Dict[str, Any]:
    """Delete a persona (stub)."""
    return {"id": pid, "deleted": True}
