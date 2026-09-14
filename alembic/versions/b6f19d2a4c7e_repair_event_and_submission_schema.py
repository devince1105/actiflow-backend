"""repair event and submission schema gaps

Revision ID: b6f19d2a4c7e
Revises: 91c0bd6f4e21
Create Date: 2026-09-14

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b6f19d2a4c7e"
down_revision: Union[str, Sequence[str], None] = "91c0bd6f4e21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add fields and enum values expected by the current models."""
    op.add_column(
        "events",
        sa.Column("location", sa.String(length=255), nullable=True),
    )

    # PostgreSQL requires enum additions outside the surrounding migration
    # transaction. IF NOT EXISTS keeps this safe for databases where these
    # values were previously added manually.
    with op.get_context().autocommit_block():
        for value in ("email_verified", "expired", "rejected"):
            op.execute(
                f"ALTER TYPE submission_status ADD VALUE IF NOT EXISTS '{value}'"
            )


def downgrade() -> None:
    """Remove the event location column.

    PostgreSQL enum values are intentionally retained: removing a value is not
    safe when existing rows may reference it.
    """
    op.drop_column("events", "location")
