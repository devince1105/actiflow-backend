import pytest
from fastapi import HTTPException
from types import SimpleNamespace

from app.core.dependencies import (
    get_current_identity,
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
