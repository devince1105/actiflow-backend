"""reconcile managed metadata baseline

Revision ID: d4e0b2c7a915
Revises: c8a41f0d2e7b
Create Date: 2026-09-15

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d4e0b2c7a915"
down_revision: Union[str, Sequence[str], None] = "c8a41f0d2e7b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _convert_utc_timestamp(table: str, column: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = '{table}'
                  AND column_name = '{column}'
                  AND data_type = 'timestamp without time zone'
            ) THEN
                ALTER TABLE {table}
                ALTER COLUMN {column}
                TYPE TIMESTAMP WITH TIME ZONE
                USING {column} AT TIME ZONE 'UTC';
            END IF;
        END
        $$
        """
    )


def upgrade() -> None:
    _convert_utc_timestamp("email_verifications", "expires_at")
    _convert_utc_timestamp("refresh_tokens", "expires_at")
    _convert_utc_timestamp("users", "email_verified_at")

    # User-profile audit values were historically varchar. Only cast values
    # that are already valid UUIDs; otherwise stop for explicit data cleanup.
    op.execute("""
        DO $$
        DECLARE
            audit_column text;
        BEGIN
            FOREACH audit_column IN ARRAY ARRAY[
                'created_by', 'updated_by', 'deleted_by'
            ]
            LOOP
                IF EXISTS (
                    SELECT 1
                    FROM user_profiles
                    WHERE NULLIF(btrim(
                        CASE audit_column
                            WHEN 'created_by' THEN created_by
                            WHEN 'updated_by' THEN updated_by
                            ELSE deleted_by
                        END
                    ), '') IS NOT NULL
                    AND (
                        CASE audit_column
                            WHEN 'created_by' THEN created_by
                            WHEN 'updated_by' THEN updated_by
                            ELSE deleted_by
                        END
                    ) !~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
                ) THEN
                    RAISE EXCEPTION
                        'user_profiles.% contains a non-UUID audit value',
                        audit_column;
                END IF;
            END LOOP;
        END
        $$
    """)
    for column in ("created_by", "updated_by", "deleted_by"):
        op.alter_column(
            "user_profiles",
            column,
            existing_type=sa.String(),
            type_=postgresql.UUID(as_uuid=True),
            postgresql_using=f"NULLIF(btrim({column}), '')::uuid",
            existing_nullable=True,
        )

    op.execute("""
        UPDATE user_profiles
        SET created_at = COALESCE(created_at, now()),
            updated_at = COALESCE(updated_at, now())
        WHERE created_at IS NULL OR updated_at IS NULL
    """)
    op.alter_column("user_profiles", "created_at", nullable=False)
    op.alter_column("user_profiles", "updated_at", nullable=False)

    # Keep existing unique constraints that back foreign keys. Add only the
    # ordinary indexes missing from migrations; equivalent unique
    # constraint/index representations are documented in alembic/env.py.
    for column in ("id", "created_by", "updated_by", "deleted_by"):
        op.create_index(f"ix_event_categories_{column}", "event_categories", [column])

    for column in ("id", "created_by", "updated_by", "deleted_by"):
        op.create_index(
            f"ix_submission_audit_logs_{column}",
            "submission_audit_logs",
            [column],
        )

    for column in ("id", "created_by", "updated_by", "deleted_by"):
        op.create_index(f"ix_user_profiles_{column}", "user_profiles", [column])

    op.create_index(
        "ix_email_verifications_token",
        "email_verifications",
        ["token"],
        unique=True,
    )
    op.create_index("ix_event_views_viewed_at", "event_views", ["viewed_at"])

    # Keep database documentation aligned with model metadata so
    # `alembic check` remains useful instead of reporting comment-only drift.
    comments = {
        ("email_verifications", "ref_uuid"): "對應資料 UUID",
        ("email_verifications", "verified_at"): None,
        ("email_verifications", "is_used"): None,
        ("event_categories", "code"): "分類代碼（例如 SPORTS_OUTDOOR）",
        ("event_categories", "slug"): "URL slug（sports-outdoor）",
        ("event_categories", "color"): "UI 顏色 token（對應前端 UIColor）",
        ("users", "email"): "使用者登入 email",
        ("users", "auth_provider"): "登入方式 (local, google, etc)",
        ("users", "avatar_url"): "使用者頭像網址",
        ("users", "config"): "Users config",
        ("users", "is_email_verified"): "是否已完成 email 驗證",
        ("users", "email_verified_at"): "email 驗證完成時間",
        ("users", "is_active"): "帳號是否啟用",
        ("users", "password_hash"): "Password hash (for local auth)",
    }
    for (table, column), comment in comments.items():
        literal = "NULL" if comment is None else "'" + comment.replace("'", "''") + "'"
        op.execute(f"COMMENT ON COLUMN {table}.{column} IS {literal}")


def downgrade() -> None:
    op.drop_index("ix_event_views_viewed_at", table_name="event_views")
    op.drop_index("ix_email_verifications_token", table_name="email_verifications")

    for column in ("id", "created_by", "updated_by", "deleted_by"):
        op.drop_index(f"ix_user_profiles_{column}", table_name="user_profiles")

    for column in ("created_by", "updated_by", "deleted_by"):
        op.alter_column(
            "user_profiles",
            column,
            existing_type=postgresql.UUID(as_uuid=True),
            type_=sa.String(),
            postgresql_using=f"{column}::text",
            existing_nullable=True,
        )

    for column in ("id", "created_by", "updated_by", "deleted_by"):
        op.drop_index(
            f"ix_submission_audit_logs_{column}",
            table_name="submission_audit_logs",
        )

    for column in ("id", "created_by", "updated_by", "deleted_by"):
        op.drop_index(f"ix_event_categories_{column}", table_name="event_categories")
