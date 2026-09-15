"""add event content jsonb

Revision ID: 7c3f575c7e0b
Revises: a6a1ee05b5d4
Create Date: 2026-01-15 19:17:15.415789

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7c3f575c7e0b'
down_revision: Union[str, Sequence[str], None] = 'a6a1ee05b5d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "events",
        sa.Column(
            "content",
            sa.dialects.postgresql.JSONB(),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("events", "content")
