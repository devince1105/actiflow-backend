# app/schemas/submission/submission_me.py

from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, EmailStr

# ============================================================
# Event（Me 用，精簡版）
# ============================================================
class MeSubmissionEvent(BaseModel):
    uuid: UUID
    slug: str
    name: str
    start_date: datetime
    end_date: Optional[datetime] = None
    location: Optional[str] = None

    model_config = {"from_attributes": True}


# ============================================================
# /users/me/submissions Response
# ============================================================
class MeSubmissionOut(BaseModel):
    """
    /users/me/submissions 專用 Response Schema
    - submitter 視角（我提交的）
    """

    uuid: UUID
    submission_code: str
    status: str
    submitted_at: datetime

    # ⭐ 正確：event 是 Event，不是 Submission
    event: Optional[MeSubmissionEvent] = None

    # ⭐ 角色資訊
    participant_email: EmailStr
    submitted_by_uuid: Optional[UUID]
    submitted_by_email: Optional[EmailStr]

    model_config = {"from_attributes": True}
