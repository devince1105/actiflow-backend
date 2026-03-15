"""add event_views table

Revision ID: adc18d20076b
Revises: 7c3f575c7e0b
Create Date: 2026-01-19 17:35:25.903647

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'adc18d20076b'
down_revision: Union[str, Sequence[str], None] = '7c3f575c7e0b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "event_views",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "event_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("events.uuid", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "viewed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("ip_address", sa.Text(), nullable=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_event_views_event_id",
        "event_views",
        ["event_id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_event_views_event_id", table_name="event_views")
    op.drop_table("event_views")
