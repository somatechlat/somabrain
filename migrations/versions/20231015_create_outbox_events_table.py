"""DEPRECATED MIGRATION FILE

This migration originally duplicated the logic in
`cf8b36c30d81_create_outbox_events_table.py`, which caused Alembic
revision‑overlap errors.  The file is kept only for historical context
but is now a **no‑op** so that Alembic can safely ignore it.
"""

from __future__ import annotations
from typing import Sequence

# Use a unique, non‑conflicting revision identifier.
revision: str = "deprecated_20231015"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """No‑op upgrade.

    The original migration is now handled by the canonical file
    `cf8b36c30d81_create_outbox_events_table.py`.  Keeping this function as a
    no‑op ensures Alembic can still import the module without applying any
    schema changes.
    """
    pass


def downgrade() -> None:
    """No‑op downgrade for the deprecated migration."""
    pass
