"""add display labels and icon to event_categories

Revision ID: a6a1ee05b5d4
Revises: c23c24cdfefb
Create Date: 2026-01-06 11:37:48.917046

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a6a1ee05b5d4'
down_revision: Union[str, Sequence[str], None] = 'c23c24cdfefb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "event_categories",
        sa.Column(
            "display_label_zh",
            sa.String(length=20),
            nullable=True,
            comment="前台顯示用短中文名稱（Tab / Pills）",
        ),
    )
    op.add_column(
        "event_categories",
        sa.Column(
            "display_label_en",
            sa.String(length=20),
            nullable=True,
            comment="前台顯示用短英文名稱（Tab / Pills）",
        ),
    )
    op.add_column(
        "event_categories",
        sa.Column(
            "icon",
            sa.String(length=50),
            nullable=True,
            comment="前台顯示用 icon（Tab / Pills）",
        ),
    )




def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("event_categories", "icon")
    op.drop_column("event_categories", "display_label_en")
    op.drop_column("event_categories", "display_label_zh")
