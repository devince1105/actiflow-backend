"""add event review workflow

Revision ID: 91c0bd6f4e21
Revises: 7f3a2d91c840
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "91c0bd6f4e21"
down_revision = "7f3a2d91c840"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "events",
        sa.Column("submitted_for_review_at", sa.DateTime(timezone=True)),
    )
    op.add_column(
        "events",
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
    )
    op.add_column(
        "events",
        sa.Column("reviewer_uuid", postgresql.UUID(as_uuid=True)),
    )
    op.add_column("events", sa.Column("review_reason", sa.Text()))
    op.create_index(
        "ix_events_review_queue",
        "events",
        ["status", "submitted_for_review_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_events_review_queue", table_name="events")
    op.drop_column("events", "review_reason")
    op.drop_column("events", "reviewer_uuid")
    op.drop_column("events", "reviewed_at")
    op.drop_column("events", "submitted_for_review_at")
