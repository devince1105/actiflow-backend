# app/schemas/event/organizer/event_create.py

from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class OrganizerEventCreate(BaseModel):
    """
    Organizer 後台建立 Event 用 Schema

    ❌ 不包含：
    - organizer_uuid（由 path / membership 注入）
    - event_code（由後端產生）
    - audit 欄位

    ✅ 僅包含 Organizer 可輸入的 domain 欄位
    """

    # 若你之後完全移除 ActivityTemplate，可直接刪掉這個欄位
    #activity_template_uuid: Optional[UUID] = None

    name: str
    description: Optional[str] = None

    start_date: datetime
    end_date: Optional[datetime] = None
    registration_deadline: Optional[datetime] = None

    # draft / published / closed
    status: str = "draft"

    # 自由 JSON（前端 Form 定義、顯示設定等）
    config: Optional[Dict[str, Any]] = None

    model_config = {
        "from_attributes": True
    }
