# app/schemas/event/category/event_category_public.py

from pydantic import BaseModel
from typing import Optional
from uuid import UUID


class EventCategoryPublic(BaseModel):
    """
    Public 用活動分類 Schema
    - 活動列表 Tabs
    - 首頁分類導覽
    - Filter 使用
    """

    uuid: UUID

    code: str
    slug: str

    label_zh: str
    label_en: Optional[str] = None

    display_label_zh: Optional[str] = None
    display_label_en: Optional[str] = None

    icon: Optional[str] = None
    color: str

    sort_order: int

    model_config = {
        "from_attributes": True
    }