"""add capacity columns to events

Revision ID: 2c675be053c5
Revises: 68de07e1ebaa
Create Date: 2026-04-25 22:10:07.215703

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2c675be053c5'
down_revision: Union[str, Sequence[str], None] = '68de07e1ebaa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add capacity columns
    op.add_column('events', sa.Column('max_capacity', sa.Integer(), nullable=False, server_default='100'))
    op.add_column('events', sa.Column('current_attendance', sa.Integer(), nullable=False, server_default='0'))

    # 2. Fill NULL event_category_uuid if any exist
    # This ensures we can safely set nullable=False in the next step
    op.execute("""
        UPDATE events
        SET event_category_uuid = (SELECT uuid FROM event_categories LIMIT 1)
        WHERE event_category_uuid IS NULL
    """)

    # 3. Sync nullability with model
    op.alter_column('events', 'event_category_uuid', nullable=False)
    op.alter_column('events', 'slug', nullable=True)


def downgrade() -> None:
    op.alter_column('events', 'slug', nullable=False)
    op.alter_column('events', 'event_category_uuid', nullable=True)
    op.drop_column('events', 'current_attendance')
    op.drop_column('events', 'max_capacity')
