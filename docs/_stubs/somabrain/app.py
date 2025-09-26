"""Lightweight stub for ``somabrain.app`` used by Sphinx.

This module intentionally exposes a tiny, stable surface so the docs build
can import ``somabrain.app`` without pulling in runtime dependencies. Keep
the module docstring simple to avoid Sphinx/ReST option-list parsing issues.
"""


def create_app():
    """Return a minimal placeholder for the FastAPI app used in the real code.

    This function intentionally returns None in the stub. The real project
    defines a richer object; the stub exists only to provide names for
    autodoc/automodule to reference during documentation generation.
    """
    return None


__all__ = ["create_app"]
