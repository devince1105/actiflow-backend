# app/api/users/me/submissions.py

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.api.auth.dependencies import get_current_user_obj
from app.models.user.user import User
from app.schemas.submission.submission_me import MeSubmissionOut
from app.crud.submission.crud_submission import submission_crud

router = APIRouter(
    prefix="/users/me/submissions",
    tags=["Users - Me - Submissions"],
)


# ============================================================
# GET /users/me/submissions
# ============================================================
@router.get(
    "",
    response_model=List[MeSubmissionOut],
    summary="取得目前登入使用者提交的報名紀錄",
)
def list_my_submissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_obj),
):
    """
    我「提交」的報名紀錄（submitter 視角）
    """
    return submission_crud.list_by_submitter(
        db=db,
        submitted_by_uuid=current_user.uuid,
    )


# ============================================================
# GET /users/me/submissions/{submission_uuid}
# ============================================================
@router.get(
    "/{submission_uuid}",
    response_model=MeSubmissionOut,
    summary="取得目前登入使用者提交的單筆報名紀錄",
)
def get_my_submission(
    submission_uuid: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_obj),
):
    """
    取得我「提交」的單筆報名紀錄
    """
    submission = submission_crud.get_by_uuid_and_submitter(
        db=db,
        submission_uuid=submission_uuid,
        submitted_by_uuid=current_user.uuid,
    )

    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")

    return submission
