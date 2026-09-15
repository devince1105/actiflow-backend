# app/api/events/public/submissions.py
from fastapi import APIRouter, Depends, Request, BackgroundTasks, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from uuid import UUID

from app.core.db import get_db
from app.api.auth.dependencies import get_optional_user
from app.services.submission.submission_service import SubmissionService
from app.schemas.submission.submission_public import (
    SubmissionPublicCreate,
    SubmissionPublicCreateResponse,
)
from app.models.submission.submission import Submission
from app.core.exceptions import ActiFlowBusinessException, ActiFlowErrorCode
from app.models.auth.email_verification import EmailVerification

from app.core.rate_limit import check_rate_limit_per_ip

router = APIRouter(
    prefix="/public/events",
    tags=["Public Event Submissions"],
)

@router.post(
    "/{event_uuid}/submissions",
    response_model=SubmissionPublicCreateResponse,
)
def create_submission(
    event_uuid: UUID,
    data: SubmissionPublicCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Public API：使用者送出活動報名
    - 處理 Atomic Capacity Control
    - 一致性 Transaction
    - 非同步 Email 發送
    - Rate Limit: 限制每分鐘單 IP 註冊次數 (Anti-Abuse)
    """
    check_rate_limit_per_ip(request, event_uuid)
    return SubmissionService.register_event(
        db=db,
        event_uuid=event_uuid,
        user_email=data.user_email,
        values=data.values,
        background_tasks=background_tasks,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        notes=data.notes,
        extra_data=data.extra_data
    )

@router.post(
    "/submissions/{submission_uuid}/confirm-email",
)
def confirm_email(
    submission_uuid: UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Public API：Email 驗證完成後，推進 Submission 狀態
    """
    verification = (
        db.query(EmailVerification)
        .filter(
            EmailVerification.ref_type == "submission",
            EmailVerification.ref_uuid == submission_uuid,
            EmailVerification.is_used == True,
            EmailVerification.verified_at.isnot(None),
        )
        .order_by(EmailVerification.created_at.desc())
        .first()
    )

    if not verification:
        raise ActiFlowBusinessException(
            code=ActiFlowErrorCode.UNAUTHORIZED,
            message="Email not verified yet",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    return SubmissionService.update_status(
        db=db,
        submission_uuid=submission_uuid,
        target_status="email_verified",
        actor_role="system",
        background_tasks=background_tasks,
    )

@router.get(
    "/{event_uuid}/status",
    response_model=dict,
)
def get_submission_status(
    event_uuid: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_optional_user),
):
    """
    Check if the current user is registered for this event.
    (Client Component 用於異步獲取使用者特定狀態，確保 SSR 分離)
    """
    if not current_user:
        return {"is_registered": False, "submission_uuid": None, "status": None}

    user_uuid = current_user.get("uuid")
    user_email = current_user.get("email")

    reg = (
        db.query(Submission)
        .filter(
            Submission.event_uuid == event_uuid,
            Submission.status != "canceled",
        )
        .filter(
            or_(
                Submission.submitted_by_uuid == user_uuid,
                Submission.user_email == user_email
            )
        )
        .first()
    )

    return {
        "is_registered": reg is not None,
        "submission_uuid": str(reg.uuid) if reg else None,
        "status": reg.status if reg else None,
    }
