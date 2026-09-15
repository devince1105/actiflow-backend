"""add event_categories and link to events

Revision ID: c23c24cdfefb
Revises: c0dfa4d0b2a0
Create Date: 2026-01-06 11:00:22.044970

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c23c24cdfefb'
down_revision: Union[str, Sequence[str], None] = 'c0dfa4d0b2a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # =====================================================
    # 1. Create event_categories table
    # =====================================================
    # =====================================================
    # 1. event_categories
    # =====================================================
    op.create_table(
        "event_categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "uuid",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=False,
            unique=True,
        ),

        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("label_zh", sa.String(length=100), nullable=False),
        sa.Column("label_en", sa.String(length=100), nullable=False),
        sa.Column("color", sa.String(length=30), nullable=False),
        sa.Column(
            "sort_order",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),

        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),

        sa.Column(
            "created_by",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "updated_by",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "deleted_by",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("created_by_role", sa.String(), nullable=True),
        sa.Column("updated_by_role", sa.String(), nullable=True),
        sa.Column("deleted_by_role", sa.String(), nullable=True),

        sa.Column(
            "version",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),

        sa.UniqueConstraint("uuid"),
        sa.UniqueConstraint("code"),
        sa.UniqueConstraint("slug"),
    )

    op.create_index(
        "ix_event_categories_code",
        "event_categories",
        ["code"],
    )
    op.create_index(
        "ix_event_categories_slug",
        "event_categories",
        ["slug"],
    )
    op.create_index(
        "ix_event_categories_sort_order",
        "event_categories",
        ["sort_order"],
    )

    # =====================================================
    # 2. events.event_category_uuid
    # =====================================================
    op.add_column(
        "events",
        sa.Column(
            "event_category_uuid",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_events_event_category_uuid",
        "events",
        ["event_category_uuid"],
    )

    op.create_foreign_key(
        "fk_events_event_category_uuid",
        source_table="events",
        referent_table="event_categories",
        local_cols=["event_category_uuid"],
        remote_cols=["uuid"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "fk_events_event_category_uuid",
        "events",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_events_event_category_uuid",
        table_name="events",
    )
    op.drop_column(
        "events",
        "event_category_uuid",
    )

    op.drop_index(
        "ix_event_categories_sort_order",
        table_name="event_categories",
    )
    op.drop_index(
        "ix_event_categories_slug",
        table_name="event_categories",
    )
    op.drop_index(
        "ix_event_categories_code",
        table_name="event_categories",
    )
    op.drop_table("event_categories")
