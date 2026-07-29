import pytest
from fastapi import HTTPException
from types import SimpleNamespace
from uuid import uuid4

from app.core.dependencies import (
    get_current_identity,
    resolve_current_organizer_context,
    require_current_organizer_admin,
    require_current_organizer_member,
    require_current_organizer_owner,
    require_super_admin,
)


def test_require_super_admin_accepts_identity_dict():
    identity = {
        "uuid": "admin-user",
        "memberships": [
            {"type": "system", "role": "super_admin"},
        ],
    }

    assert require_super_admin(identity) == identity


def test_require_super_admin_rejects_regular_identity():
    identity = {
        "uuid": "regular-user",
        "memberships": [
            {"type": "system", "role": "user"},
        ],
    }

    with pytest.raises(HTTPException) as exc_info:
        require_super_admin(identity)

    assert exc_info.value.status_code == 403


def test_require_super_admin_rejects_legacy_system_admin_role():
    identity = {
        "uuid": "legacy-admin",
        "memberships": [
            {"type": "system", "role": "system_admin"},
        ],
    }

    with pytest.raises(HTTPException) as exc_info:
        require_super_admin(identity)

    assert exc_info.value.status_code == 403


def test_get_current_identity_keeps_canonical_identity_dict():
    identity = {"uuid": "user-1", "memberships": []}

    assert get_current_identity(identity) is identity


@pytest.mark.parametrize("role", ["owner", "admin"])
def test_organizer_admin_accepts_management_roles(role):
    membership = SimpleNamespace(role=role)

    assert require_current_organizer_admin(membership) is membership


def test_organizer_admin_rejects_member():
    with pytest.raises(HTTPException) as exc_info:
        require_current_organizer_admin(SimpleNamespace(role="member"))

    assert exc_info.value.status_code == 403


@pytest.mark.parametrize("role", ["owner", "admin", "member"])
def test_organizer_member_accepts_supported_roles(role):
    membership = SimpleNamespace(role=role)

    assert require_current_organizer_member(membership) is membership


def test_organizer_owner_is_owner_only():
    owner = SimpleNamespace(role="owner")
    assert require_current_organizer_owner(owner) is owner

    with pytest.raises(HTTPException) as exc_info:
        require_current_organizer_owner(SimpleNamespace(role="admin"))

    assert exc_info.value.status_code == 403


def test_organizer_member_rejects_unsupported_legacy_role():
    with pytest.raises(HTTPException) as exc_info:
        require_current_organizer_member(SimpleNamespace(role="editor"))

    assert exc_info.value.status_code == 403


class _RecordingQuery:
    def __init__(self, result):
        self.result = result
        self.filters = []

    def filter(self, *conditions):
        self.filters.extend(conditions)
        return self

    def first(self):
        return self.result


class _RecordingDb:
    def __init__(self, result):
        self.query_result = _RecordingQuery(result)

    def query(self, _model):
        return self.query_result


def test_organizer_context_scopes_membership_to_active_path_organizer():
    organizer_uuid = uuid4()
    membership = SimpleNamespace(role="member")
    db = _RecordingDb(membership)

    result = resolve_current_organizer_context(
        organizer_uuid=organizer_uuid,
        db=db,
        identity={"uuid": uuid4()},
    )

    assert result is membership
    filters = " ".join(str(condition) for condition in db.query_result.filters)
    assert "organizer_memberships.organizer_uuid" in filters
    assert "organizer_memberships.user_uuid" in filters
    assert "organizer_memberships.is_active" in filters
    assert "organizer_memberships.is_deleted" in filters
    assert "organizer_memberships.is_suspended" in filters
    assert "organizer_memberships.role" in filters


def test_organizer_context_rejects_missing_or_ineligible_membership():
    db = _RecordingDb(None)

    with pytest.raises(HTTPException) as exc_info:
        resolve_current_organizer_context(
            organizer_uuid=uuid4(),
            db=db,
            identity={"uuid": uuid4()},
        )

    assert exc_info.value.status_code == 403
