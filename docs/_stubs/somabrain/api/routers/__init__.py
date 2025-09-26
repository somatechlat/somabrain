"""Lightweight package stub for somabrain.api.routers used by Sphinx.

This package is used only during documentation builds to avoid executing
runtime-only code at import time. It should mirror the public symbols
exported by the real package but contain no heavy imports.
"""

__all__ = ["link", "persona", "rag"]

# Expose submodules as package attributes to support both
# `import somabrain.api.routers.rag` and `from somabrain.api.routers import rag`
try:
    from . import link  # type: ignore
    from . import persona  # type: ignore
    from . import rag  # type: ignore
except Exception:
    # Best-effort placeholder imports; Sphinx's autodoc_mock_imports will
    # still handle heavy runtime imports when necessary.
    pass
