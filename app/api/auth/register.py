from datetime import datetime, timedelta, timezone
import secrets

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.utils.email_verification_mailer import send_verification_email
from app.core.db import get_db
from app.core.exceptions import ActiFlowBusinessException, ActiFlowErrorCode
from app.core.security import hash_password
from app.models.auth.email_verification import EmailVerification
from app.models.user.user import User
from app.schemas.auth.register_request import RegisterRequest
from app.schemas.auth.register_response import RegisterResponse


router = APIRouter(tags=["Auth"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_user(
    data: RegisterRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    email = data.email.strip().lower()
    existing = (
        db.query(User.uuid)
        .filter(func.lower(User.email) == email, User.is_deleted == False)
        .first()
    )
    if existing:
        raise ActiFlowBusinessException(
            code=ActiFlowErrorCode.ALREADY_REGISTERED,
            message="此 Email 已註冊",
            status_code=status.HTTP_409_CONFLICT,
        )

    user = User(
        email=email,
        password_hash=hash_password(data.password),
        auth_provider="local",
        config={"display_name": data.name.strip()} if data.name else {},
        is_email_verified=False,
    )
    db.add(user)
    db.flush()

    token = secrets.token_urlsafe(32)
    db.add(
        EmailVerification(
            ref_type="user",
            ref_uuid=user.uuid,
            email=email,
            token=token,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
    )
    db.commit()
    db.refresh(user)

    background_tasks.add_task(
        send_verification_email,
        to_email=email,
        token=token,
    )
    return RegisterResponse(
        status="verification_required",
        email=user.email,
    )
