# alembic/env.py
from logging.config import fileConfig
from alembic import context
from sqlalchemy import pool

from app.core.db import engine, Base
import app.models  # 讓所有 model 被載入，填滿 Base.metadata

print("ALEMBIC ENGINE URL =", engine.url)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# These objects are intentionally retained for backward-compatible data
# access, but are no longer managed by current ORM models. Keeping the
# allowlist explicit prevents Alembic autogenerate from proposing destructive
# legacy cleanup while still checking every actively managed object.
LEGACY_TABLES = {"platforms"}
LEGACY_COLUMNS = {
    ("email_verifications", "user_uuid"),
    ("users", "last_login_at"),
    ("users", "name"),
    ("users", "phone"),
    ("users", "provider_id"),
}
# These pairs use different physical implementations with equivalent
# guarantees (unique constraint plus lookup index versus a unique index).
# Alembic otherwise proposes replacing them on every autogenerate run.
EQUIVALENT_SCHEMA_OBJECTS = {
    "event_categories_code_key",
    "event_categories_slug_key",
    "event_categories_uuid_key",
    "ix_event_categories_code",
    "ix_event_categories_slug",
    "ix_event_categories_uuid",
    "submission_audit_logs_uuid_key",
    "ix_submission_audit_logs_uuid",
    "user_profiles_user_uuid_key",
    "user_profiles_uuid_key",
    "ix_user_profiles_user_uuid",
    "ix_user_profiles_uuid",
}


def include_object(object_, name, type_, reflected, compare_to):
    table = getattr(object_, "table", None)
    table_name = getattr(table, "name", None)

    if type_ == "table" and name in LEGACY_TABLES:
        return False
    if type_ in {"index", "unique_constraint"} and name in EQUIVALENT_SCHEMA_OBJECTS:
        return False
    if type_ == "column" and (table_name, name) in LEGACY_COLUMNS:
        return False
    if reflected and type_ in {"index", "foreign_key_constraint"}:
        columns = getattr(object_, "columns", ())
        if any((table_name, column.name) in LEGACY_COLUMNS for column in columns):
            return False
    return True

def run_migrations_offline() -> None:
    url = str(engine.url)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_comments=False,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_comments=False,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
