# app/schemas/event/organizer/event_update.py

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class OrganizerEventUpdate(BaseModel):
    """
    Organizer 後台更新 Event 用 Schema（PATCH）

    設計原則：
    - ❌ 不包含 organizer_uuid / event_code / audit 欄位
    - ✅ 僅包含 Organizer 可修改欄位
    - ✅ 同時支援「前端相容欄位」與「Domain 標準欄位」
    - ⚠️ 欄位衝突的處理邏輯交由 CRUD 層統一收斂
    """

    # ------------------------------------------------------------------
    # 🔹 Domain 標準欄位（DB / Model 最終認可）
    # ------------------------------------------------------------------
    name: Optional[str] = Field(
        None,
        description="活動名稱（修改後會重新產生 slug）",
    )

    description: Optional[str] = Field(
        None,
        description="活動描述",
    )

    start_date: Optional[datetime] = Field(
        None,
        description="活動開始時間",
    )

    end_date: Optional[datetime] = Field(
        None,
        description="活動結束時間",
    )

    registration_deadline: Optional[datetime] = Field(
        None,
        description="報名截止時間",
    )

    status: Optional[str] = Field(
        None,
        description="活動狀態（draft / published / closed）",
    )

    config: Optional[Dict[str, Any]] = Field(
        None,
        description="活動設定（表單結構 / 前端顯示用 JSON）",
    )

    # ------------------------------------------------------------------
    # 🔹 前端相容欄位（僅為過渡用途）
    # ------------------------------------------------------------------
    title: Optional[str] = Field(
        None,
        description="前端舊欄位：對應 name",
    )

    event_start_at: Optional[datetime] = Field(
        None,
        description="前端舊欄位：對應 start_date",
    )

    event_end_at: Optional[datetime] = Field(
        None,
        description="前端舊欄位：對應 end_date",
    )

    registration_start_at: Optional[datetime] = Field(
        None,
        description="前端舊欄位：目前未使用（保留相容）",
    )

    registration_end_at: Optional[datetime] = Field(
        None,
        description="前端舊欄位：對應 registration_deadline",
    )

    # ------------------------------------------------------------------
    # Pydantic v2 設定
    # ------------------------------------------------------------------
    model_config = {
        "from_attributes": True,
        "extra": "forbid",  # 🚫 防止前端亂丟欄位
    }
