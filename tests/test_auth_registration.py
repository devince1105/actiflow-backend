from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.auth.email_verification import EmailVerification
from app.models.user.user import User


def test_register_verify_and_login(client, db: Session, monkeypatch):
    sent = []
    monkeypatch.setattr(
        "app.api.auth.register.send_verification_email",
        lambda **kwargs: sent.append(kwargs),
    )
    email = f"member+{uuid4().hex}@example.com"
    password = "correct-horse-123"

    registered = client.post(
        "/auth/register",
        json={
            "email": email.upper(),
            "password": password,
            "name": "測試會員",
        },
    )
    assert registered.status_code == 201
    assert registered.json() == {
        "status": "verification_required",
        "email": email,
    }
    assert sent and sent[0]["to_email"] == email

    user = db.query(User).filter(User.email == email).one()
    assert user.is_email_verified is False
    assert user.config["display_name"] == "測試會員"

    blocked = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert blocked.status_code == 403
    assert blocked.json()["code"] == "EMAIL_NOT_VERIFIED"

    verification = (
        db.query(EmailVerification)
        .filter(
            EmailVerification.ref_type == "user",
            EmailVerification.ref_uuid == user.uuid,
        )
        .one()
    )
    verified = client.post(
        "/auth/email-verification/verify",
        json={"token": verification.token},
    )
    assert verified.status_code == 200
    assert verified.json()["status"] == "verified"

    db.refresh(user)
    assert user.is_email_verified is True
    assert user.email_verified_at is not None

    logged_in = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert logged_in.status_code == 200


def test_register_rejects_duplicate_email(client, db: Session, monkeypatch):
    monkeypatch.setattr(
        "app.api.auth.register.send_verification_email",
        lambda **_kwargs: None,
    )
    email = f"duplicate+{uuid4().hex}@example.com"
    payload = {"email": email, "password": "password-123"}

    assert client.post("/auth/register", json=payload).status_code == 201
    duplicate = client.post(
        "/auth/register",
        json={**payload, "email": email.upper()},
    )

    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "ALREADY_REGISTERED"
