# app/api/users/me/participations.py

from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.api.auth.dependencies import get_current_user_obj
from app.models.user.user import User
from app.schemas.submission.submission_me import MeSubmissionOut
from app.crud.submission.crud_submission import submission_crud

router = APIRouter(
    prefix="/users/me/participations",
    tags=["Users - Me - Participations"],
)


# ============================================================
# GET /users/me/participations
# ============================================================
@router.get(
    "",
    response_model=List[MeSubmissionOut],
    summary="取得目前登入使用者實際參與的活動紀錄",
)
def list_my_participations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_obj),
):
    """
    我「實際參與」的報名紀錄
    """
    return submission_crud.list_participations_by_user(
        db=db,
        user_uuid=current_user.uuid,
    )
