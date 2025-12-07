"""Stub submodule for sqlalchemy.types used in the test suite.

Provides a minimal ``Text`` placeholder that mirrors the class defined in the
top‑level ``sqlalchemy`` stub. The real SQLAlchemy library offers many more
types, but the codebase only requires ``Text`` for JSON column definitions.
"""

from . import Text  # Re‑export the ``Text`` placeholder from the package root.
