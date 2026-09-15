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

    # 2. Guarantee a deterministic fallback before backfilling historical
    # events. A database can legitimately have events but no category rows at
    # this point in the migration chain.
    op.execute("""
        INSERT INTO event_categories (
            uuid,
            code,
            slug,
            label_zh,
            label_en,
            color,
            sort_order,
            is_active,
            is_deleted,
            version
        )
        SELECT
            '00000000-0000-0000-0000-000000000001'::uuid,
            'UNCATEGORIZED',
            'uncategorized',
            '未分類',
            'Uncategorized',
            'slate',
            9999,
            TRUE,
            FALSE,
            1
        WHERE EXISTS (
            SELECT 1 FROM events WHERE event_category_uuid IS NULL
        )
        AND NOT EXISTS (SELECT 1 FROM event_categories)
        ON CONFLICT DO NOTHING
    """)

    # 3. Fill NULL event_category_uuid if any exist.
    op.execute("""
        UPDATE events
        SET event_category_uuid = (
            SELECT uuid
            FROM event_categories
            ORDER BY sort_order, id
            LIMIT 1
        )
        WHERE event_category_uuid IS NULL
    """)

    # 4. Restore capacity from historical submissions instead of silently
    # treating every existing event as empty.
    op.execute("""
        UPDATE events AS event
        SET current_attendance = (
            SELECT COUNT(*)
            FROM submissions AS submission
            WHERE submission.event_uuid = event.uuid
              AND submission.is_deleted = FALSE
              AND submission.status::text IN ('pending', 'paid', 'completed')
        )
    """)

    # 5. Sync nullability with model
    op.alter_column('events', 'event_category_uuid', nullable=False)
    op.alter_column('events', 'slug', nullable=True)


def downgrade() -> None:
    op.alter_column('events', 'slug', nullable=False)
    op.alter_column('events', 'event_category_uuid', nullable=True)
    op.drop_column('events', 'current_attendance')
    op.drop_column('events', 'max_capacity')
