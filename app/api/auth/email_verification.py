from datetime import datetime, timedelta, timezone
import secrets

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.utils.email_verification_mailer import send_verification_email
from app.core.db import get_db
from app.models.auth.email_verification import EmailVerification
from app.models.user.user import User


router = APIRouter(
    prefix="/auth/email-verification",
    tags=["Auth - Email Verification"],
)

TOKEN_TTL = timedelta(hours=24)
RESEND_COOLDOWN = timedelta(seconds=60)


class VerifyUserEmailRequest(BaseModel):
    token: str = Field(min_length=16, max_length=255)


class ResendUserEmailRequest(BaseModel):
    email: EmailStr


@router.post("/verify")
def verify_user_email(
    data: VerifyUserEmailRequest,
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    verification = (
        db.query(EmailVerification)
        .filter(
            EmailVerification.token == data.token,
            EmailVerification.ref_type == "user",
            EmailVerification.is_deleted == False,
        )
        .first()
    )
    if not verification:
        raise HTTPException(status_code=400, detail="驗證連結無效")

    user = (
        db.query(User)
        .filter(
            User.uuid == verification.ref_uuid,
            User.is_deleted == False,
        )
        .first()
    )
    if not user:
        raise HTTPException(status_code=400, detail="找不到對應會員")

    if user.is_email_verified:
        return {"status": "verified", "already_verified": True}

    expires_at = verification.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if verification.is_used or expires_at < now:
        raise HTTPException(status_code=400, detail="驗證連結已失效，請重新寄送")

    verification.is_used = True
    verification.verified_at = now
    user.is_email_verified = True
    user.email_verified_at = now
    db.commit()
    return {"status": "verified", "already_verified": False}


@router.post("/resend", status_code=status.HTTP_202_ACCEPTED)
def resend_user_verification(
    data: ResendUserEmailRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Always return the same response so account existence is not disclosed."""
    email = data.email.strip().lower()
    user = (
        db.query(User)
        .filter(
            func.lower(User.email) == email,
            User.is_deleted == False,
        )
        .first()
    )
    response = {
        "status": "accepted",
        "message": "若此 Email 尚未驗證，我們會寄出新的驗證信",
    }
    if not user or user.is_email_verified:
        return response

    latest = (
        db.query(EmailVerification)
        .filter(
            EmailVerification.ref_type == "user",
            EmailVerification.ref_uuid == user.uuid,
            EmailVerification.is_deleted == False,
        )
        .order_by(EmailVerification.created_at.desc())
        .first()
    )
    now = datetime.now(timezone.utc)
    if latest:
        created_at = latest.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if now - created_at < RESEND_COOLDOWN:
            return response

    (
        db.query(EmailVerification)
        .filter(
            EmailVerification.ref_type == "user",
            EmailVerification.ref_uuid == user.uuid,
            EmailVerification.is_used == False,
            EmailVerification.is_deleted == False,
        )
        .update({EmailVerification.is_used: True})
    )
    token = secrets.token_urlsafe(32)
    db.add(
        EmailVerification(
            ref_type="user",
            ref_uuid=user.uuid,
            email=user.email,
            token=token,
            expires_at=now + TOKEN_TTL,
        )
    )
    db.commit()
    background_tasks.add_task(
        send_verification_email,
        to_email=user.email,
        token=token,
    )
    return response
