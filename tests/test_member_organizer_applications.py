from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.organizer.organizer_application import OrganizerApplication
from app.models.organizer.organizer import Organizer
from app.models.membership.organizer_membership import OrganizerMembership
from app.models.user.user import User


def _login_member(client, db: Session, *, verified: bool) -> User:
    password = "member-password-123"
    user = User(
        email=f"organizer-applicant+{uuid4().hex}@example.com",
        password_hash=hash_password(password),
        is_active=True,
        is_email_verified=verified,
        auth_provider="local",
        config={},
    )
    db.add(user)
    db.commit()
    response = client.post(
        "/auth/login",
        json={"email": user.email, "password": password},
    )
    if verified:
        assert response.status_code == 200
    return user


def test_verified_member_can_submit_and_list_organizer_application(
    client,
    db: Session,
):
    user = _login_member(client, db, verified=True)
    payload = {
        "name": "城市行動協會",
        "description": "推動城市居民參與戶外活動與社區交流的非營利團隊。",
        "reason": "希望使用平台建立公開活動、管理報名者並留下完整審核紀錄。",
        "contact_email": user.email,
        "phone": "02-1234-5678",
        "website": "https://example.com",
        "address": "台北市中正區",
    }

    created = client.post(
        "/users/me/organizer-applications",
        json=payload,
    )
    assert created.status_code == 201
    assert created.json()["name"] == payload["name"]
    assert created.json()["status"] == "pending"
    assert created.json()["application_reason"] == payload["reason"]

    saved = (
        db.query(OrganizerApplication)
        .filter(OrganizerApplication.user_uuid == user.uuid)
        .one()
    )
    assert saved.application_data["email"] == user.email
    assert saved.created_by == user.uuid

    listed = client.get("/users/me/organizer-applications")
    assert listed.status_code == 200
    assert listed.json()[0]["uuid"] == created.json()["uuid"]

    duplicate = client.post(
        "/users/me/organizer-applications",
        json=payload,
    )
    assert duplicate.status_code == 409

    from app.core.dependencies import require_super_admin
    from app.main import app

    admin = User(
        email=f"reviewer+{uuid4().hex}@example.com",
        password_hash=hash_password("admin-password-123"),
        is_active=True,
        is_email_verified=True,
        auth_provider="local",
        config={},
    )
    db.add(admin)
    db.commit()
    admin_identity = {
        "uuid": str(admin.uuid),
        "email": admin.email,
        "memberships": [{"type": "system", "role": "super_admin"}],
    }
    app.dependency_overrides[require_super_admin] = lambda: admin_identity
    try:
        approved = client.post(
            f"/admin/organizers/applications/{saved.uuid}/approve",
            json={"reason": "資料完整，核准建立組織"},
        )
    finally:
        app.dependency_overrides.pop(require_super_admin, None)

    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    organizer = db.query(Organizer).filter(Organizer.name == payload["name"]).one()
    assert organizer.address == {"formatted": payload["address"]}
    membership = (
        db.query(OrganizerMembership)
        .filter(
            OrganizerMembership.user_uuid == user.uuid,
            OrganizerMembership.organizer_uuid == organizer.uuid,
        )
        .one()
    )
    assert membership.role == "owner"


def test_unverified_member_cannot_submit_organizer_application(
    client,
    db: Session,
):
    user = User(
        email=f"unverified-applicant+{uuid4().hex}@example.com",
        password_hash=hash_password("member-password-123"),
        is_active=True,
        is_email_verified=False,
        auth_provider="local",
        config={},
    )
    db.add(user)
    db.commit()

    # Exercise the endpoint dependency directly by overriding authentication:
    from app.api.auth.dependencies import get_current_user_obj
    from app.main import app

    app.dependency_overrides[get_current_user_obj] = lambda: user
    try:
        response = client.post(
            "/users/me/organizer-applications",
            json={
                "name": "尚未驗證團隊",
                "description": "這是一段足夠長的組織說明，用來驗證未驗證會員不能送件。",
                "reason": "這是一段足夠長的申請原因，用來確認 Email 驗證權限邊界。",
            },
        )
    finally:
        app.dependency_overrides.pop(get_current_user_obj, None)

    assert response.status_code == 403
