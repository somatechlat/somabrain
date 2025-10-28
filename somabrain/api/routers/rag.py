"""Deprecated router (removed).

This module is intentionally inert. The legacy /rag endpoint has been retired in
favor of the unified /memory/recall API. Importing this module will raise an
error to make the removal explicit and prevent accidental use.
"""

raise RuntimeError(
    "The legacy /rag router has been removed. Use /memory/recall instead."
)
