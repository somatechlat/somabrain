"""SomaBrain API service wrapper.

The existing FastAPI application lives in ``somabrain.app``.  Importing
``services.sb.app`` returns that ASGI application so deployment tooling
can rely on the new service layout without breaking current imports.
"""

from somabrain.app import app  # re-export for ASGI tooling

__all__ = ["app"]
