"""Tenant-aware outbox uniqueness and indices

Revision ID: b5c9f9a3d1ab
Revises: 7f1a2b3c4d89
Create Date: 2025-11-14 11:45:00.000000
"""

from __future__ import annotations
from typing import Sequence
from alembic import op

revision: str = "b5c9f9a3d1ab"
down_revision: str | None = "7f1a2b3c4d89"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("outbox_events") as batch_op:
        batch_op.drop_constraint("outbox_events_dedupe_key_key", type_="unique")
        batch_op.create_unique_constraint(
            "uq_outbox_tenant_dedupe", ["tenant_id", "dedupe_key"]
        )
    op.create_index(
        "ix_outbox_status_tenant_created",
        "outbox_events",
        ["status", "tenant_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_outbox_status_tenant_created",
        table_name="outbox_events",
    )
    with op.batch_alter_table("outbox_events") as batch_op:
        batch_op.drop_constraint("uq_outbox_tenant_dedupe", type_="unique")
        batch_op.create_unique_constraint(
            "outbox_events_dedupe_key_key", ["dedupe_key"]
        )
