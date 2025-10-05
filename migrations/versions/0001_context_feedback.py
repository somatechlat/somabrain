"""Initial schema for context feedback and token ledger."""

from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0001_context_feedback"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """TODO: Add docstring."""
    op.create_table(
        "feedback_events",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("session_id", sa.String(length=128), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=False),
        sa.Column("utility", sa.Float(), nullable=False),
        sa.Column("reward", sa.Float(), nullable=True),
        sa.Column("metadata_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_feedback_events_session_id", "feedback_events", ["session_id"], unique=False
    )
    op.create_table(
        "token_usage",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("session_id", sa.String(length=128), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=True),
        sa.Column("tokens", sa.Float(), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_token_usage_session_id", "token_usage", ["session_id"], unique=False
    )


def downgrade() -> None:
    """TODO: Add docstring."""
    op.drop_index("ix_token_usage_session_id", table_name="token_usage")
    op.drop_table("token_usage")
    op.drop_index("ix_feedback_events_session_id", table_name="feedback_events")
    op.drop_table("feedback_events")
