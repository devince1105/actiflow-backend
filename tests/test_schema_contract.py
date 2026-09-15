from sqlalchemy import inspect


def test_submission_integrity_constraints_exist(db):
    inspector = inspect(db.get_bind())

    unique_constraints = {
        constraint["name"]
        for constraint in inspector.get_unique_constraints("submissions")
    }
    assert "uq_submission_event_code" in unique_constraints
    assert "uq_submission_event_user_email" in unique_constraints

    foreign_keys = {
        foreign_key["name"]: foreign_key
        for foreign_key in inspector.get_foreign_keys("submissions")
    }
    assert foreign_keys["fk_submissions_event_uuid_events"]["referred_table"] == "events"
    assert foreign_keys["fk_submissions_user_uuid_users"]["referred_table"] == "users"


def test_submission_code_lookup_index_is_not_globally_unique(db):
    inspector = inspect(db.get_bind())
    indexes = {
        index["name"]: index
        for index in inspector.get_indexes("submissions")
    }

    assert indexes["ix_submissions_submission_code"]["unique"] is False


def test_submission_child_foreign_keys_exist(db):
    inspector = inspect(db.get_bind())

    value_foreign_keys = {
        foreign_key["name"]
        for foreign_key in inspector.get_foreign_keys("submission_values")
    }
    assert "fk_submission_values_submission_uuid_submissions" in value_foreign_keys
    assert "fk_submission_values_event_field_uuid_event_fields" in value_foreign_keys

    file_foreign_keys = {
        foreign_key["name"]
        for foreign_key in inspector.get_foreign_keys("submission_files")
    }
    assert "fk_submission_files_submission_uuid_submissions" in file_foreign_keys
    assert (
        "fk_submission_files_submission_value_uuid_submission_values"
        in file_foreign_keys
    )
    assert "fk_submission_files_file_uuid_files" in file_foreign_keys
