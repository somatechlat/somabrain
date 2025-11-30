from __future__ import annotations
from typing import Sequence
from alembic import op
import sqlalchemy as sa

"""Add cog_global_frames and cog_segments tables

Revision ID: 3c1a2b4c5d67
Revises: cf8b36c30d81
Create Date: 2025-10-26 12:00:00.000000

"""


# revision identifiers, used by Alembic.
revision: str = "3c1a2b4c5d67"
down_revision: str | None = "cf8b36c30d81"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Global frames: store leader, weights, frame map, rationale
    op.create_table(
        "cog_global_frames",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tenant", sa.String(length=128), nullable=True),
        sa.Column("leader", sa.String(length=32), nullable=False),
        sa.Column("weights", sa.JSON(), nullable=False),
        sa.Column("frame", sa.JSON(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_cog_global_frames_tenant_ts",
        "cog_global_frames",
        ["tenant", "ts"],
        unique=False,
    )

    # Segments: boundary events
    op.create_table(
        "cog_segments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("boundary_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("domain", sa.String(length=32), nullable=False),
        sa.Column("dwell_ms", sa.Integer(), nullable=False),
        sa.Column("evidence", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_cog_segments_boundary_ts",
        "cog_segments",
        ["boundary_ts"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_cog_segments_boundary_ts", table_name="cog_segments")
    op.drop_table("cog_segments")
    op.drop_index("ix_cog_global_frames_tenant_ts", table_name="cog_global_frames")
    op.drop_table("cog_global_frames")
