"""add submitted_by fields to submissions

Revision ID: c45aa2330403
Revises: adc18d20076b
Create Date: 2026-01-20 17:28:02.755171

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c45aa2330403'
down_revision: Union[str, Sequence[str], None] = 'adc18d20076b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("submissions", sa.Column("submitted_by_uuid", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("submissions", sa.Column("submitted_by_email", sa.String(), nullable=True))

    op.create_index("ix_submissions_submitted_by_uuid", "submissions", ["submitted_by_uuid"])
    op.create_index("ix_submissions_submitted_by_email", "submissions", ["submitted_by_email"])

    op.create_foreign_key(
        "fk_submissions_submitted_by_uuid_users",
        "submissions",
        "users",
        ["submitted_by_uuid"],
        ["uuid"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("fk_submissions_submitted_by_uuid_users", "submissions", type_="foreignkey")
    op.drop_index("ix_submissions_submitted_by_email", table_name="submissions")
    op.drop_index("ix_submissions_submitted_by_uuid", table_name="submissions")
    op.drop_column("submissions", "submitted_by_email")
    op.drop_column("submissions", "submitted_by_uuid")
