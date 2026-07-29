import pytest
from fastapi import HTTPException

from app.core.dependencies import require_super_admin


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
