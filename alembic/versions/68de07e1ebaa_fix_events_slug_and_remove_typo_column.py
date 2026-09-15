"""fix events slug and remove typo column

Revision ID: 68de07e1ebaa
Revises: c45aa2330403
Create Date: 2026-01-20 22:29:47.103624

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '68de07e1ebaa'
down_revision: Union[str, Sequence[str], None] = 'c45aa2330403'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # --------------------------------------------------
    # 1. 新增 slug 欄位（先允許 NULL）
    # --------------------------------------------------
    op.add_column(
        "events",
        sa.Column("slug", sa.String(length=255), nullable=True),
    )
    op.create_index(
        "ix_events_slug",
        "events",
        ["slug"],
        unique=True,
    )

    # --------------------------------------------------
    # 2. 用 event_code 補 slug
    # --------------------------------------------------
    op.execute("""
        UPDATE events
        SET slug = event_code
        WHERE slug IS NULL
    """)

    # --------------------------------------------------
    # 3. 安全移除拼寫錯誤欄位 aactivity_template_uuid
    # --------------------------------------------------
    op.execute("""
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1
            FROM pg_constraint
            WHERE conname = 'events_aactivity_template_uuid_fkey'
        ) THEN
            ALTER TABLE events
            DROP CONSTRAINT events_aactivity_template_uuid_fkey;
        END IF;
    END$$;
    """)

    op.drop_index(
        "ix_events_aactivity_template_uuid",
        table_name="events",
    )

    op.drop_column(
        "events",
        "aactivity_template_uuid",
    )

    # --------------------------------------------------
    # 4. 最後再把 slug 收為 NOT NULL
    # --------------------------------------------------
    op.alter_column(
        "events",
        "slug",
        nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    # downgrade 只需做到「可回滾」，不必完美還原資料
    op.add_column(
        "events",
        sa.Column("aactivity_template_uuid", sa.UUID(), nullable=True),
    )
    op.create_index(
        "ix_events_aactivity_template_uuid",
        "events",
        ["aactivity_template_uuid"],
    )

    op.alter_column(
        "events",
        "slug",
        nullable=True,
    )
    op.drop_index("ix_events_slug", table_name="events")
    op.drop_column("events", "slug")
