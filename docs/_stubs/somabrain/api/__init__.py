"""Lightweight stubs for somabrain.api used by Sphinx builds.

Expose a minimal `routers` namespace so autosummary can find
`somabrain.api.routers.*` modules without importing the real package.
"""

__all__ = ["routers"]

# Provide a small routers package placeholder. Individual router stubs live
# under docs/_stubs/somabrain/api/routers/*.py
try:
    from . import routers  # type: ignore
except Exception:
    pass
