"""Lightweight package for Sphinx stub imports.

This package intentionally exposes a small set of submodules and symbols so
that autosummary and autodoc can import attributes like ``somabrain.thalamus``
without importing the full runtime package. Keep this file minimal and
side-effect free.
"""

__all__ = ["app", "thalamus", "api"]

# Expose commonly-referenced submodules as attributes on the package to
# satisfy autosummary's attribute lookups (it sometimes tries to access
# submodules via the parent package). Importing here is safe because these
# modules live under docs/_stubs and are lightweight placeholders.
try:
    from . import api  # type: ignore
    from . import app  # type: ignore
    from . import thalamus  # type: ignore
except Exception:
    # Best-effort; if the imports fail we still want Sphinx to continue and
    # rely on autodoc_mock_imports to suppress heavy imports.
    pass
