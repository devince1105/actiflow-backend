from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.auth.refresh_token import RefreshToken
from app.models.user.user import User


PASSWORD = "test-session-password"


def _create_user(db: Session, *, active: bool = True) -> User:
    user = User(
        uuid=uuid4(),
        email=f"session+{uuid4().hex}@test.com",
        password_hash=hash_password(PASSWORD),
        is_active=active,
        is_email_verified=True,
        auth_provider="local",
        config={},
        version=1,
    )
    db.add(user)
    db.commit()
    return user


def _login(client, user: User):
    return client.post(
        "/auth/login",
        json={"email": user.email, "password": PASSWORD},
    )


def test_inactive_user_cannot_log_in(client, db: Session):
    user = _create_user(db, active=False)

    response = _login(client, user)

    assert response.status_code == 401
    assert "refresh_token" not in client.cookies


def test_refresh_rotates_token_and_rejects_replay(client, db: Session):
    user = _create_user(db)
    assert _login(client, user).status_code == 200
    old_token = client.cookies.get("refresh_token")

    response = client.post("/auth/refresh")

    assert response.status_code == 200
    assert "access_token" not in response.json()
    new_token = client.cookies.get("refresh_token")
    assert new_token and new_token != old_token
    old_record = (
        db.query(RefreshToken)
        .filter(RefreshToken.token == old_token)
        .one()
    )
    assert old_record.revoked is True

    client.cookies.clear()
    client.cookies.set("refresh_token", old_token)
    assert client.post("/auth/refresh").status_code == 401


def test_expired_refresh_token_is_rejected(client, db: Session):
    user = _create_user(db)
    assert _login(client, user).status_code == 200
    token_value = client.cookies.get("refresh_token")
    token = (
        db.query(RefreshToken)
        .filter(RefreshToken.token == token_value)
        .one()
    )
    token.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()

    assert client.post("/auth/refresh").status_code == 401


def test_logout_revokes_refresh_token_and_clears_session(client, db: Session):
    user = _create_user(db)
    assert _login(client, user).status_code == 200
    token_value = client.cookies.get("refresh_token")

    response = client.post("/auth/logout")

    assert response.status_code == 200
    token = (
        db.query(RefreshToken)
        .filter(RefreshToken.token == token_value)
        .one()
    )
    assert token.revoked is True
    assert "access_token" not in client.cookies
    assert "refresh_token" not in client.cookies


def test_disabling_user_invalidates_existing_access_cookie(client, db: Session):
    user = _create_user(db)
    assert _login(client, user).status_code == 200
    user.is_active = False
    db.commit()

    assert client.get("/auth/me").status_code == 404


def test_password_change_revokes_current_refresh_token(client, db: Session):
    user = _create_user(db)
    assert _login(client, user).status_code == 200
    token_value = client.cookies.get("refresh_token")

    response = client.put(
        "/users/me/account-settings/password",
        json={
            "current_password": PASSWORD,
            "new_password": "a-new-session-password",
        },
    )

    assert response.status_code == 200
    token = (
        db.query(RefreshToken)
        .filter(RefreshToken.token == token_value)
        .one()
    )
    assert token.revoked is True
    assert client.post("/auth/refresh").status_code == 401
