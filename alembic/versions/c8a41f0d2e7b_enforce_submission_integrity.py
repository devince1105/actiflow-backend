"""enforce submission integrity

Revision ID: c8a41f0d2e7b
Revises: b6f19d2a4c7e
Create Date: 2026-09-14

"""

from typing import Sequence, Union

from alembic import op


revision: str = "c8a41f0d2e7b"
down_revision: Union[str, Sequence[str], None] = "b6f19d2a4c7e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Canonicalize the value used by the per-event uniqueness constraint.
    op.execute("""
        UPDATE submissions
        SET user_email = lower(trim(user_email))
        WHERE user_email <> lower(trim(user_email))
    """)

    # Never choose a winner for duplicate registrations in a migration. Stop
    # with an actionable error so an operator can resolve the records safely.
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM submissions
                GROUP BY event_uuid, user_email
                HAVING COUNT(*) > 1
            ) THEN
                RAISE EXCEPTION
                    'duplicate submissions exist for the same event and email';
            END IF;

            IF EXISTS (
                SELECT 1
                FROM submissions
                GROUP BY event_uuid, submission_code
                HAVING COUNT(*) > 1
            ) THEN
                RAISE EXCEPTION
                    'duplicate submission codes exist within the same event';
            END IF;

            IF EXISTS (
                SELECT 1
                FROM submissions AS submission
                LEFT JOIN events AS event
                    ON event.uuid = submission.event_uuid
                WHERE event.uuid IS NULL
            ) THEN
                RAISE EXCEPTION 'orphan submissions reference missing events';
            END IF;

            IF EXISTS (
                SELECT 1
                FROM submissions AS submission
                LEFT JOIN users AS app_user
                    ON app_user.uuid = submission.user_uuid
                WHERE submission.user_uuid IS NOT NULL
                  AND app_user.uuid IS NULL
            ) THEN
                RAISE EXCEPTION 'orphan submissions reference missing users';
            END IF;

            IF EXISTS (
                SELECT 1
                FROM submission_values AS submission_value
                LEFT JOIN submissions AS submission
                    ON submission.uuid = submission_value.submission_uuid
                WHERE submission.uuid IS NULL
            ) THEN
                RAISE EXCEPTION
                    'orphan submission values reference missing submissions';
            END IF;

            IF EXISTS (
                SELECT 1
                FROM submission_values AS submission_value
                LEFT JOIN event_fields AS event_field
                    ON event_field.uuid = submission_value.event_field_uuid
                WHERE event_field.uuid IS NULL
            ) THEN
                RAISE EXCEPTION
                    'orphan submission values reference missing event fields';
            END IF;

            IF EXISTS (
                SELECT 1
                FROM submission_files AS submission_file
                LEFT JOIN submissions AS submission
                    ON submission.uuid = submission_file.submission_uuid
                WHERE submission.uuid IS NULL
            ) THEN
                RAISE EXCEPTION
                    'orphan submission files reference missing submissions';
            END IF;

            IF EXISTS (
                SELECT 1
                FROM submission_files AS submission_file
                LEFT JOIN submission_values AS submission_value
                    ON submission_value.uuid = submission_file.submission_value_uuid
                WHERE submission_file.submission_value_uuid IS NOT NULL
                  AND submission_value.uuid IS NULL
            ) THEN
                RAISE EXCEPTION
                    'orphan submission files reference missing submission values';
            END IF;

            IF EXISTS (
                SELECT 1
                FROM submission_files AS submission_file
                LEFT JOIN files AS stored_file
                    ON stored_file.uuid = submission_file.file_uuid
                WHERE stored_file.uuid IS NULL
            ) THEN
                RAISE EXCEPTION
                    'orphan submission files reference missing files';
            END IF;
        END
        $$
    """)

    # The initial migration accidentally made submission codes globally
    # unique. Keep a lookup index, but enforce the model's event-scoped rule.
    op.drop_index(
        "ix_submissions_submission_code",
        table_name="submissions",
    )
    op.create_index(
        "ix_submissions_submission_code",
        "submissions",
        ["submission_code"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_submission_event_code",
        "submissions",
        ["event_uuid", "submission_code"],
    )
    op.create_unique_constraint(
        "uq_submission_event_user_email",
        "submissions",
        ["event_uuid", "user_email"],
    )

    op.create_foreign_key(
        "fk_submissions_event_uuid_events",
        "submissions",
        "events",
        ["event_uuid"],
        ["uuid"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_submissions_user_uuid_users",
        "submissions",
        "users",
        ["user_uuid"],
        ["uuid"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_submission_values_submission_uuid_submissions",
        "submission_values",
        "submissions",
        ["submission_uuid"],
        ["uuid"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_submission_values_event_field_uuid_event_fields",
        "submission_values",
        "event_fields",
        ["event_field_uuid"],
        ["uuid"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_submission_files_submission_uuid_submissions",
        "submission_files",
        "submissions",
        ["submission_uuid"],
        ["uuid"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_submission_files_submission_value_uuid_submission_values",
        "submission_files",
        "submission_values",
        ["submission_value_uuid"],
        ["uuid"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_submission_files_file_uuid_files",
        "submission_files",
        "files",
        ["file_uuid"],
        ["uuid"],
        ondelete="CASCADE",
    )

    # Include enum values introduced after the original capacity migration.
    op.execute("""
        UPDATE events AS event
        SET current_attendance = (
            SELECT COUNT(*)
            FROM submissions AS submission
            WHERE submission.event_uuid = event.uuid
              AND submission.is_deleted = FALSE
              AND submission.status::text IN (
                  'pending', 'email_verified', 'paid', 'completed'
              )
        )
    """)


def downgrade() -> None:
    op.drop_constraint(
        "fk_submission_files_file_uuid_files",
        "submission_files",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_submission_files_submission_value_uuid_submission_values",
        "submission_files",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_submission_files_submission_uuid_submissions",
        "submission_files",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_submission_values_event_field_uuid_event_fields",
        "submission_values",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_submission_values_submission_uuid_submissions",
        "submission_values",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_submissions_user_uuid_users",
        "submissions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_submissions_event_uuid_events",
        "submissions",
        type_="foreignkey",
    )
    op.drop_constraint(
        "uq_submission_event_user_email",
        "submissions",
        type_="unique",
    )
    op.drop_constraint(
        "uq_submission_event_code",
        "submissions",
        type_="unique",
    )
    op.drop_index(
        "ix_submissions_submission_code",
        table_name="submissions",
    )
    op.create_index(
        "ix_submissions_submission_code",
        "submissions",
        ["submission_code"],
        unique=True,
    )
