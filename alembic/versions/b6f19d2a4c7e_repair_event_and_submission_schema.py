"""repair event and submission schema gaps

Revision ID: b6f19d2a4c7e
Revises: 91c0bd6f4e21
Create Date: 2026-09-14

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b6f19d2a4c7e"
down_revision: Union[str, Sequence[str], None] = "91c0bd6f4e21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add fields and enum values expected by the current models."""
    # The enum autocommit block below can leave this DDL committed if a later
    # migration fails. IF NOT EXISTS makes a deployment retry safe.
    op.execute(
        "ALTER TABLE events ADD COLUMN IF NOT EXISTS location VARCHAR(255)"
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
    op.execute("ALTER TABLE events DROP COLUMN IF EXISTS location")
