"""Alembic revision template."""
from __future__ import annotations

from typing import Sequence

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
