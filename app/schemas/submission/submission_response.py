# app/schemas/submission/submission_response.py

from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from app.schemas.submission.submission_base import SubmissionBase
from app.schemas.submission.submission_value import SubmissionValueResponse
from app.models.submission.enums import SubmissionStatus

class SubmissionResponse(SubmissionBase):
    """
    Organizer / Admin 後台最終回傳的 Submission 資料格式
    - 繼承 SubmissionBase（保留所有共用欄位）
    - 加上 values（submission values）
    - 加上 JOIN user 資訊
    """

    uuid: UUID
    submission_code: str
    status: SubmissionStatus
    created_at: datetime

    # JOIN User 資訊（後台需要）
    user_name: Optional[str]
    user_email: Optional[str]

    # 每一筆 submission 對應的欄位值
    values: List[SubmissionValueResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}
