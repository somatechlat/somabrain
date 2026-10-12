"""Environment-based settings loader."""

from .base import *  # noqa: F403,F405  (Django settings composition)

# Optional: Load environment specific overrides if needed,
# but base.py already aggregates the core logic.
# This keeps it simple and predictable.
