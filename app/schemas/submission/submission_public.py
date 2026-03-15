# app/schemas/submission/submission_public.py

from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from app.schemas.submission.submission_value import (
    SubmissionValuePublic,
    SubmissionValuePublicCreate,
)

# ============================================================
# Public Create（送出報名表單）
# ============================================================
class SubmissionPublicCreate(BaseModel):
    """
    Public Submission Create 用 schema

    設計說明：
    - Public 使用者送出報名表單
    - user_email = 實際參加者 / 被報名者
    - submitted_by_* 由後端依登入狀態補齊
    """

    user_email: EmailStr
    values: List[SubmissionValuePublicCreate]

    notes: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None


# ============================================================
# Public Read（查詢 / 顯示）
# ============================================================
class SubmissionPublic(BaseModel):
    """
    Public Submission Read（v1）

    語意說明：
    - submission 由誰提交（submitted_by）
    - 實際參加者是誰（participant）
    """

    uuid: UUID
    submission_code: str

    event_uuid: UUID
    status: str
    submitted_at: Optional[datetime]

    # ⭐ 角色欄位（關鍵）
    participant_email: EmailStr
    submitted_by_uuid: Optional[UUID]
    submitted_by_email: Optional[EmailStr]

    # 表單內容
    values: List[SubmissionValuePublic] = []

    model_config = {"from_attributes": True}


# ============================================================
# Public Create Response（送出後立即回傳）
# ============================================================
class SubmissionPublicCreateResponse(BaseModel):
    """
    Public Submission Create Response

    設計說明：
    - 僅回傳建立完成後「一定存在」的欄位
    - 避免回傳 values（JOIN / field_type 複雜度）
    """

    uuid: UUID
    submission_code: str
    status: str

    model_config = {"from_attributes": True}
