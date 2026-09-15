"""add submission audit logs

Revision ID: 7f3a2d91c840
Revises: 2c675be053c5
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "7f3a2d91c840"
down_revision = "2c675be053c5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Historical databases can contain duplicate registrations. Enforcing a
    # new constraint here would make the audit-table migration impossible to
    # deploy and would require destructive cleanup. The service rejects new
    # duplicates; legacy cleanup and a database constraint belong in a
    # dedicated, reviewed data migration.
    op.create_table(
        "submission_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("uuid", postgresql.UUID(as_uuid=True), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", postgresql.UUID(as_uuid=True)),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True)),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True)),
        sa.Column("created_by_role", sa.String()),
        sa.Column("updated_by_role", sa.String()),
        sa.Column("deleted_by_role", sa.String()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("submission_uuid", postgresql.UUID(as_uuid=True), sa.ForeignKey("submissions.uuid", ondelete="CASCADE"), nullable=False),
        sa.Column("actor_uuid", postgresql.UUID(as_uuid=True)),
        sa.Column("actor_role", sa.String(), nullable=False),
        sa.Column("action_type", sa.String(), nullable=False),
        sa.Column("old_status", sa.String()),
        sa.Column("new_status", sa.String(), nullable=False),
        sa.Column("reason", sa.Text()),
        sa.Column("extra_data", postgresql.JSONB(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_submission_audit_logs_submission_uuid", "submission_audit_logs", ["submission_uuid"])
    op.create_index("ix_submission_audit_logs_actor_uuid", "submission_audit_logs", ["actor_uuid"])


def downgrade() -> None:
    op.drop_table("submission_audit_logs")
